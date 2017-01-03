# -*- coding: utf-8 -*-
from AccessControl import getSecurityManager
from Queue import Empty
from Queue import Queue
from collective.taskqueue.interfaces import ITaskQueue
from plone.memoize import forever
from transaction import get as get_transaction
from transaction.interfaces import ISavepoint
from transaction.interfaces import ISavepointDataManager
from zope.component import ComponentLookupError
from zope.component import getUtilitiesFor
from zope.component import getUtility
from zope.globalrequest import getRequest
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary
import logging
import urllib
import urlparse
import uuid

logger = logging.getLogger('collective.taskqueue')

_marker = object()


class DummySavepoint:
    implements(ISavepoint)

    valid = property(lambda self: self.transaction is not None)

    def __init__(self, datamanager):
        self.datamanager = datamanager

    def rollback(self):
        pass


class TaskQueueTransactionDataManager(object):

    implements(ISavepointDataManager)

    _COUNTER = 0

    def __init__(self, queue, task):
        self.queue = queue
        self.task = task

        self.sort_key = '~collective.taskqueue.{0:d}'.format(
            TaskQueueTransactionDataManager._COUNTER)
        TaskQueueTransactionDataManager._COUNTER += 1

    def commit(self, t):
        pass

    def sortKey(self):
        return self.sort_key

    def abort(self, t):
        pass

    def tpc_begin(self, t):
        pass

    def tpc_vote(self, t):
        pass

    def tpc_finish(self, t):
        self.queue.put(self.task)

    def tpc_abort(self, t):
        pass

    def savepoint(self):
        return DummySavepoint(self)


class TaskQueueBase(object):

    transaction_data_manager = TaskQueueTransactionDataManager

    @property
    @forever.memoize
    def name(self):
        vocabulary =\
            getUtility(IVocabularyFactory, 'collective.taskqueue.queues')()
        for term in vocabulary:
            if term.value == self:
                return term.token
        return None

    def add(self, url=None, method='GET', params=None, headers=None,
            payload=_marker):
        task_id, task = make_task(url, method, params, headers, payload)
        get_transaction().join(self.transaction_data_manager(self, task))
        return task_id


class LocalVolatileTaskQueue(TaskQueueBase):

    implements(ITaskQueue)

    def __init__(self, **kwargs):
        self.queue = Queue()

    def __len__(self):
        return self.queue.qsize()

    def put(self, task):
        self.queue.put(task, block=True)

    def get(self, *args, **kwargs):
        try:
            return self.queue.get(block=False)
        except Empty:
            return None

    def task_done(self, *args, **kwargs):
        self.queue.task_done()

    def reset(self):
        self.queue = Queue()


class TaskQueuesVocabulary(object):

    implements(IVocabularyFactory)

    def __call__(self, context=None):
        utilities = getUtilitiesFor(ITaskQueue)
        items = [(unicode(name), queue) for name, queue in utilities]
        return SimpleVocabulary.fromItems(items)


def make_task(url=None, method='GET', params=None, headers=None,
              payload=_marker):
    assert url, 'Url not given'

    request = getRequest()
    headers = headers or {}
    params = params or {}

    if params:
        parts = list(urlparse.urlparse(url))
        parts[4] = '&'.join(filter(bool, [parts[4],  # 4 == query
                                          urllib.urlencode(params)]))
        url = urlparse.urlunparse(parts)

    # Copy HTTP-headers from request._orig_env:
    env = (getattr(request, '_orig_env', None) or {}).copy()
    for key, value in env.items():
        if key.startswith('HTTP_'):
            key = '-'.join(map(str.capitalize, key[5:].split('_')))
            if key != 'User-Agent' and not key in headers:
                headers[key] = value
        elif key.startswith('CONTENT_') and payload is _marker:
            key = '-'.join(map(str.capitalize, key.split('_')))
            headers[key] = value

    # Copy payload from re-seekable StringIO when not explicitly given:
    if payload is _marker and request.stdin is not None and type(request.stdin) is not file:  # noqa
        request.stdin.seek(0)
        payload = request.stdin.read()
        request.stdin.seek(0)
    elif payload is _marker:
        payload = ''

    # Set special X-Task-Id -header to identify each message
    headers['X-Task-Id'] = str(uuid.uuid4())

    # Set special X-Task-User-Id -header for Task Queue PAS plugin
    task_user_id = getSecurityManager().getUser().getId()
    if bool(task_user_id):
        headers['X-Task-User-Id'] = task_user_id

    def safe_str(s):
        if isinstance(s, bool):
            return str(s).lower()
        elif isinstance(s, unicode):
            return s.encode('utf-8', 'replace')
        else:
            return str(s)

    # Build task dictionary
    task = {
        'url': url,  # Physical /Plone/to/callable with optional querystring
        'method': method,  # GET or POST
        'headers': ['{0:s}: {1:s}'.format(key, safe_str(value))
                    for key, value in sorted(headers.items())],
        'payload': payload
    }

    return headers['X-Task-Id'], task


def add(url=None, method='GET', params=None, headers=None, payload=_marker,
        queue=_marker):

    vocabulary =\
        getUtility(IVocabularyFactory, "collective.taskqueue.queues")()
    assert len(vocabulary), u"No task queues defined. Cannot queue task."
    fallback = sorted(tuple(vocabulary.by_token))[0]

    if queue is _marker:
        queue = fallback
    try:
        task_queue = getUtility(ITaskQueue, name=queue)
    except ComponentLookupError:
        logger.warning("TaskQueue '%s' not found. "
                       "Adding to '%s' queue instead.",
                       queue, fallback)
        task_queue = getUtility(ITaskQueue, name=fallback)

    return task_queue.add(url, method, params, headers, payload)


def reset(queue=_marker):

    vocabulary = \
        getUtility(IVocabularyFactory, "collective.taskqueue.queues")()
    assert len(vocabulary), u"No task queues defined. Cannot reset queue."
    fallback = sorted(tuple(vocabulary.by_token))[0]

    if queue is _marker:
        queue = fallback
    try:
        task_queue = getUtility(ITaskQueue, name=queue)
    except ComponentLookupError:
        logger.warning("TaskQueue '%s' not found. "
                       "Resetting queue '%s' instead.",
                       queue, fallback)
        task_queue = getUtility(ITaskQueue, name=fallback)
    task_queue.reset()
