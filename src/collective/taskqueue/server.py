from collective.taskqueue.config import TASK_QUEUE_SERVER_IDENT
from collective.taskqueue.interfaces import ITaskQueue
from collective.taskqueue.interfaces import ITaskQueueLayer
from io import BytesIO
from twisted.application.service import IService
from twisted.application.service import Service
from twisted.internet import reactor
from twisted.internet import threads
from twisted.internet.defer import DeferredLock
from twisted.logger import Logger
from twisted.python.runtime import seconds
from twisted.web.http import _escape
from twisted.web.http import datetimeToLogString
from twisted.web.wsgi import _ErrorStream
from twisted.web.wsgi import _InputStream
from twisted.web.wsgi import _wsgiString
from zope.component import ComponentLookupError
from zope.component import getUtility
from zope.interface import implementer
from ZPublisher import WSGIPublisher
from ZPublisher.HTTPRequest import HTTPRequest

import logging


logger = logging.getLogger("collective.taskqueue")


def make_environ(task):
    headers = {}
    for header in task["headers"]:
        name, value = header.split(": ", 1)
        if name not in headers:
            headers[name] = value
        else:
            headers[name] = ",".join([headers[name], value])

    environ = {
        "REQUEST_METHOD": _wsgiString(task["method"]),
        "REMOTE_ADDR": _wsgiString("127.0.0.1"),
        "SCRIPT_NAME": _wsgiString(""),
        "PATH_INFO": _wsgiString(task["url"].split("?", 1)[0]),
        "QUERY_STRING": _wsgiString(task["url"].split("?", 1)[-1]),
        "CONTENT_TYPE": _wsgiString(headers["Content-Type"]),
        "CONTENT_LENGTH": _wsgiString(headers["Content-Length"]),
        "SERVER_NAME": _wsgiString(headers["Host"].split(":", 1)[0]),
        "SERVER_PORT": _wsgiString(headers["Host"].split(":", 1)[-1]),
        "SERVER_PROTOCOL": _wsgiString("HTTP/1.1"),
        "SERVER_SOFTWARE": TASK_QUEUE_SERVER_IDENT,
    }

    headers["User-Agent"] = TASK_QUEUE_SERVER_IDENT
    for name, value in headers.items():
        name = "HTTP_" + _wsgiString(name).upper().replace("-", "_")
        # It might be preferable for http.HTTPChannel to clear out newlines.
        environ[name] = _wsgiString(value).replace("\n", " ")

    if isinstance(task["payload"], bytes):
        payload = task["payload"]
    else:
        payload = task["payload"].encode("UTF-8")
    environ.update(
        {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.run_once": False,
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.errors": _ErrorStream(),
            "wsgi.input": _InputStream(BytesIO(payload)),
        }
    )

    return environ


def make_access_log_line(status_line, response_headers, task):
    headers = dict([header.split(":", 1) for header in task["headers"]])
    headers.update(dict(response_headers))
    headers["User-Agent"] = TASK_QUEUE_SERVER_IDENT
    ip = "127.0.0.1"
    referrer = _escape(headers.get("Referer") or "-").strip()
    agent = _escape(headers.get("User-Agent") or "-")
    timestamp = seconds()
    line = (
        '"%(ip)s" - - %(timestamp)s "%(method)s %(uri)s %(protocol)s" '
        '%(code)s %(length)s "%(referrer)s" "%(agent)s"'
        % dict(
            ip=_escape(ip),
            timestamp=datetimeToLogString(timestamp),
            method=_escape(task["method"]),
            uri=_escape(task["url"]),
            protocol=_escape("HTTP/1.1"),
            code=status_line.split()[0],
            length=headers.get("Content-Length") or "-",
            referrer=referrer,
            agent=agent,
        )
    )
    return line


@implementer(ITaskQueueLayer)
class TaskRequest(HTTPRequest):
    """TaskQueue Request"""


@implementer(IService)
class TaskQueueServer(Service):
    # required by ZServer
    SERVER_IDENT = TASK_QUEUE_SERVER_IDENT

    def __init__(
        self,
        name="default",
        queue="default",
        concurrent_limit=1,
        retry_max_count=10,
        publish_module=None,
        access_logger=None,
    ):
        # Use given publish_module instead of WSGIPublisher.publish_module
        # to support integration tests
        self.publish_module = publish_module or WSGIPublisher.publish_module
        self.access_logger = access_logger or Logger()
        self.access_logger.info("TaskQueueServer started")

        # Init settings
        self.name = "collective.taskqueue:server:" + name
        self.queue = queue
        self.concurrent_limit = concurrent_limit
        self.concurrent_tasks = 0
        self.retry_max_count = retry_max_count

        # Init locks required when calling worker threads
        self.task_acknowledgement_mutex = DeferredLock()

    def startService(self):
        super().startService()
        for i in range(self.concurrent_limit):
            self.consume_task_from_queue()

    def consume_task_from_queue(self):
        queue = self.get_task_queue()
        d = queue.get(consumer_name=self.name)
        d.addCallback(self.dispatch)

    def get_task_queue(self):
        try:
            task_queue = getUtility(ITaskQueue, name=self.queue)
        except ComponentLookupError:
            task_queue = getUtility(ITaskQueue, name="default")
        return task_queue

    def dispatch(self, task):
        self.concurrent_limit += 1

        # Decode encoded payload
        def decode(obj):
            if isinstance(obj, bytes):
                return obj.decode("utf-8")
            elif isinstance(obj, list):
                return [decode(o) for o in obj]
            return obj

        task = {
            decode(key): decode(value) if key not in ["payload", b"payload"] else value
            for key, value in task.items()
        }

        environ = make_environ(task)

        def request_factory(*args, **kwargs):
            request = TaskRequest(*args, **kwargs)
            request.retry_max_count = self.retry_max_count
            return request

        d = threads.deferToThread(
            self.publish_module,
            environ,
            lambda *args: reactor.callFromThread(
                lambda *args_, t=task: self.start_response(*args_, task=t),
                *args,
                t=task,
            ),
            _request_factory=request_factory,
        )
        d.addCallback(lambda *args, t=task: self.finish_response(*args, task=t))

    def start_response(self, status, headers, excInfo=None, task=None):
        task["response"] = {"status": status, "headers": headers}
        if self.access_logger is not None:
            self.access_logger.info(make_access_log_line(status, headers, task))

    def finish_response(self, app_iter, task=None):
        self.concurrent_limit -= 1
        self.consume_task_from_queue()

        status_line = task["response"]["status"]
        response_headers = dict(task["response"]["headers"])

        # Acknowledge done task for queue with expected consumer state
        task.pop("response", None)  # Restore task its origin state
        task_queue = self.get_task_queue()
        self.task_acknowledgement_mutex.run(
            task_queue.task_done,
            task,
            status_line=status_line,
            consumer_name=self.name,
            consumer_length=self.concurrent_limit,
        )

        # Log warning when HTTP 3xx
        if status_line.startswith("3") and "Location" in response_headers:
            logger.warning(
                "{:s} ({:s} --> {:s} [not followed])".format(
                    status_line, task["url"], response_headers["Location"]
                )
            )

        # Log error when not HTTP 2xx
        elif not status_line.startswith("2"):
            logger.error("{:s} ({:s})".format(status_line, task["url"]))
