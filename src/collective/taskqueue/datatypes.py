# -*- coding: utf-8 -*-
from collective.taskqueue.config import TASK_QUEUE_SERVER_IDENT
from collective.taskqueue.config import HAS_REDIS
from collective.taskqueue.config import HAS_MSGPACK


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
        return TASK_QUEUE_SERVER_IDENT

    def create(self):
        from ZServer.AccessLogger import access_logger
        from collective.taskqueue.server import TaskQueueServer
        return TaskQueueServer(name=self.name,
                               queue=self.queue,
                               concurrent_limit=self.concurrent_limit,
                               retry_max_count=self.retry_max_count,
                               access_logger=access_logger)
