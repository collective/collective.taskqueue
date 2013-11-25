# -*- coding: utf-8 -*-
from zope.component import provideUtility
from collective.taskqueue.config import TASK_QUEUE_IDENT
from collective.taskqueue.config import TASK_QUEUE_SERVER_IDENT
from collective.taskqueue.config import HAS_REDIS
from collective.taskqueue.config import HAS_MSGPACK
from collective.taskqueue.interfaces import ITaskQueue


class TaskQueueFactory(object):

    def __init__(self, section):
        self.ip = None
        self.port = None
        self.host = None
        self.server_name = TASK_QUEUE_IDENT

        self.queue = section.queue
        self.type = section.type
        self.kwargs = {
            'host': section.host,
            'port': section.port,
            'db': section.db,
            'password': section.password,
            'unix_socket_path': section.unix_socket_path
        }

        # Drop empty or conflicting kwargs
        for key in [k for k in self.kwargs if self.kwargs[k] in ('', None)]:
            self.kwargs.pop(key)
        if self.kwargs.get('unix_socket_path'):
            self.kwargs.pop('host')
            self.kwargs.pop('port')

        if self.queue == 'redis':
            assert HAS_REDIS, (
                'Redis-queues require redis-package. '
                'Please, require collective.taskqueue using '
                '"collective.taskqueue [redis]" to get all the dependencies.')
            assert HAS_MSGPACK, (
                'Redis-queues require msgpack-python-package. '
                'Please, require collective.taskqueue using '
                '"collective.taskqueue [redis]" to get all the dependencies.')

    def prepare(self, *args, **kwargs):
        return

    def servertype(self):
        return self.server_name

    def create(self):
        if not '.' in self.type:
            mod = __import__('collective.taskqueue', fromlist=[self.type])
            klass = getattr(mod, self.type)
        else:
            mod = __import__(self.type[:self.type.rfind('.')],
                             fromlist=[self.type[self.type.rfind('.') + 1:]])
            klass = getattr(mod, self.type[self.type.rfind('.') + 1:])
        task_queue = klass(**self.kwargs)
        provideUtility(task_queue, ITaskQueue, name=self.queue)

        # Support plone.app.debugtoolbar:
        task_queue.ip = self.ip
        task_queue.port = self.port
        task_queue.server_name = '%s:%s' % (self.server_name, self.queue)

        return task_queue


class TaskQueueServerFactory(object):

    def __init__(self, section):
        self.ip = None
        self.port = None
        self.host = None
        self.server_name = TASK_QUEUE_SERVER_IDENT

        self.name = section.name
        self.queue = section.queue
        self.concurrent_limit = section.concurrent_limit
        self.retry_max_count = section.retry_max_count

        if self.queue == 'redis':
            assert HAS_REDIS, (
                'Redis-queues require redis-package. '
                'Please, require collective.taskqueue using '
                '"collective.taskqueue [redis]" to get all the dependencies.')
            assert HAS_MSGPACK, (
                'Redis-queues require msgpack-python-package. '
                'Please, require collective.taskqueue using '
                '"collective.taskqueue [redis]" to get all the dependencies.')

    def prepare(self, *args, **kwargs):
        return

    def servertype(self):
        return self.server_name

    def create(self):
        from ZServer.AccessLogger import access_logger
        from collective.taskqueue.server import TaskQueueServer
        server = TaskQueueServer(name=self.name,
                                 queue=self.queue,
                                 concurrent_limit=self.concurrent_limit,
                                 retry_max_count=self.retry_max_count,
                                 access_logger=access_logger)

        # Support plone.app.debugtoolbar:
        server.ip = self.ip
        server.port = self.port
        server.server_name = '%s:%s' % (self.server_name, self.queue)

        return server
