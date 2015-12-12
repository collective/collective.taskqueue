# -*- coding: utf-8 -*-
import asyncore
import os
import time
import socket
import StringIO
import posixpath
import logging
import threading

from ZServer.ClockServer import LogHelper
from ZServer.PubCore.ZEvent import Wakeup
from ZServer.medusa.http_server import http_request
from ZServer.medusa.default_handler import unquote
from ZServer.PubCore import handle
from ZServer.HTTPResponse import make_response
from ZPublisher.HTTPRequest import HTTPRequest
from zope.component import getUtility
from zope.component import ComponentLookupError
from zope.interface import implements

from collective.taskqueue.config import TASK_QUEUE_SERVER_IDENT
from collective.taskqueue.config import HAS_REDIS
from collective.taskqueue.interfaces import ITaskQueueLayer
from collective.taskqueue.interfaces import ITaskQueue

logger = logging.getLogger('collective.taskqueue')


class TaskQueueServer(asyncore.dispatcher):

    # required by ZServer
    SERVER_IDENT = TASK_QUEUE_SERVER_IDENT

    def __init__(self, name='default', queue='default', concurrent_limit=1,
                 retry_max_count=10, handler=None, access_logger=None):
        # Use given handler instead of ZPublisher.PubCore.handle
        # to support integration tests
        self.handler = handler or handle

        # Set access logger
        if access_logger:
            self.logger = LogHelper(access_logger)
        else:
            class DummyLogger(object):
                def log(self, *args):
                    pass
            self.logger = DummyLogger()

        # Identify the main thread
        self.ident = threading.currentThread().ident

        # Init unfinished tasks counter
        self.unfinished_tasks_mutex = threading.Lock()
        self.unfinished_tasks = 0

        # Init settings
        self.name = name
        self.queue = queue
        self.concurrent_limit = concurrent_limit
        self.retry_max_count = retry_max_count

        # Init asyncore.dispatcher
        asyncore.dispatcher.__init__(self)
        self._readable = None  # set by the first self.readable()

        # Create dummy socket to join into asyncore loop
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self._dummy_socket = self.socket

    def _set_readable_redis(self, task_queue):
        redis_connected = False

        import redis
        try:
            # Subscribe to Redis queue events
            task_queue.pubsub.subscribe(task_queue.redis_key)
            task_queue.pubsub.connection._sock.setblocking(0)
            redis_connected = True
        except redis.ConnectionError:
            # Try again in the next asyncore loop iteration
            pass

        if redis_connected:
            # Replace initial dummy socket with Redis PubSub socket
            self.del_channel()
            # XXX: Because the following line mutates asyncore map within poll,
            # it's important that the currently mapped socket remains open.
            self.set_socket(task_queue.pubsub.connection._sock)
            self._readable = True
            logger.info("TaskQueueServer listening to Redis events for "
                        "Redis queue '%s'." % task_queue.redis_key)

    def get_task_queue(self):
        try:
            task_queue = getUtility(ITaskQueue, name=self.queue)
        except ComponentLookupError:
            task_queue = getUtility(ITaskQueue, name='default')
        return task_queue

    def readable(self):
        task_queue = self.get_task_queue()

        # Init asyncore dispatcher readability
        if self._readable is None:
            if HAS_REDIS:
                from collective.taskqueue.redisqueue import RedisTaskQueue
                if issubclass(task_queue.__class__, RedisTaskQueue):
                    # Configure asyncore socket map to poll Redis events
                    self._set_readable_redis(task_queue)
                else:
                    self._readable = False
            else:
                self._readable = False

        # Poll task queue
        if self.unfinished_tasks_mutex.acquire(False):  # don't block, but skip
            try:
                if (self.concurrent_limit == 0
                        or self.unfinished_tasks < self.concurrent_limit):
                    task = task_queue.get(consumer_name=self.name)
                    if task is not None:
                        self.unfinished_tasks += 1
                        self.dispatch(task)
            finally:
                self.unfinished_tasks_mutex.release()

        return bool(self._readable)

    def dispatch(self, task):
        req, zreq, resp = make_request_and_response(self, task)
        self.handler('Zope2', zreq, resp)

    def handle_read(self):
        if bool(self._readable) and len(self.get_task_queue()) < 1:
            try:
                self.recv(4096)
            except socket.error:
                pass

    def writable(self):
        return False

    def handle_write(self):
        pass

    def handle_close(self, force=False):
        if bool(self._readable):
            logger.warning('TaskQueueServer disconnected.')
            # Reset dispatcher into initial dummy state to trigger reconnect
            self.del_channel()
            self.socket.close()
            self._dummy_socket.close()
            self._readable = None
            if not force:
                self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
                self._dummy_socket = self.socket
        else:
            asyncore.dispatcher.handle_close(self)

    def handle_error(self):
        if bool(self._readable):
            asyncore.dispatcher.handle_error(self)


def make_request_and_response(server, task):
    payload = StringIO.StringIO()
    if task['payload'] is not None:
        payload.write(task['payload'])
        payload.seek(0)
    additional_headers = ['User-Agent: {0:s}'.format(TASK_QUEUE_SERVER_IDENT)]
    req = '{0:s} {1:s} HTTP/{2:s}'.format(task['method'], task['url'], '1.1')
    req = http_request(TaskChannel(server, task), req,
                       task['method'], task['url'], '1.1',
                       task['headers'] + additional_headers)
    env = make_env(req, task['method'])
    resp = make_response(req, env)
    task_request = TaskRequest(payload, env, resp)
    task_request.retry_max_count = server.retry_max_count
    return req, task_request, resp


def make_env(req, method='GET'):
    (path, params, query, fragment) = req.split_uri()
    if params:
        path = path + params  # Undo Medusa bug.
    while path and path[0] == '/':
        path = path[1:]
    if '%' in path:
        path = unquote(path)
    if query:
        # ZPublisher doesn't want the leading '?'.
        query = query[1:]

    env = dict(GATEWAY_INTERFACE='CGI/1.1',
               REMOTE_ADDR='0',
               REQUEST_METHOD=method,
               SCRIPT_NAME='',
               SERVER_NAME='nohost',
               SERVER_PORT='',
               SERVER_PROTOCOL='HTTP/1.1',
               SERVER_SOFTWARE='Zope',
               HTTP_USER_AGENT=TASK_QUEUE_SERVER_IDENT)
    env['PATH_INFO'] = '/' + path
    env['PATH_TRANSLATED'] = posixpath.normpath(
        posixpath.join(os.getcwd(), env['PATH_INFO']))
    if query:
        env['QUERY_STRING'] = query
    env['channel.creation_time'] = time.time()

    for header in req.header:
        key, value = header.split(':', 1)
        key = key.upper()
        value = value.strip()
        if key.startswith('CONTENT-'):
            key = '{0:s}'.format('_'.join(key.split('-')))
        else:
            key = 'HTTP_{0:s}'.format('_'.join(key.split('-')))
        if value:
            env[key] = value

    return env


class TaskRequest(HTTPRequest):

    implements(ITaskQueueLayer)


class TaskChannel(object):
    """Medusa channel for TaskQueue server"""

    addr = ['127.0.0.1']
    closed = 0

    def __init__(self, server, task):
        self.server = server
        self.task = task
        self.output = ''

    def push(self, producer, *args):
        # Collect task output
        if type(producer) == str:
            self.output += producer
        else:
            self.output += producer.more()

    def done(self):
        # Read status line from output
        status_line = self.output.split('\r\n').pop(0)

        # Acknowledge done task for queue with expected consumer state
        task_queue = self.server.get_task_queue()

        # Acquire lock when not the main thread
        try:
            if self.server.ident != threading.currentThread().ident:
                self.server.unfinished_tasks_mutex.acquire()

            self.server.unfinished_tasks -= 1
            task_queue.task_done(self.task,
                                 status_line=status_line,
                                 consumer_name=self.server.name,
                                 consumer_length=self.server.unfinished_tasks)

        finally:
            # Release lock when not the main thread
            if self.server.ident != threading.currentThread().ident:
                self.server.unfinished_tasks_mutex.release()

        # Signal that mutex is free and queue can be polled again
        Wakeup()

        # Log warning when HTTP 3xx
        if status_line.startswith('HTTP/1.1 3'):
            pos = self.output.find('Location: ')
            location = self.output[max(0, pos):].split('\r\n').pop(0)
            logger.warning('{0:s} ({1:s} --> {2:s} [not followed])'.format(
                status_line, self.task['url'], location[10:]))

        # Log error when not HTTP 2xx
        elif not status_line.startswith('HTTP/1.1 2'):
            logger.error('{0:s} ({1:s})'.format(
                status_line, self.task['url']))
