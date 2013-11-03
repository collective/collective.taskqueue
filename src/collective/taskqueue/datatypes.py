# -*- coding: utf-8 -*-
from collective.taskqueue.config import TASK_QUEUE_SERVER_IDENT


class TaskQueueServerFactory(object):

    def __init__(self, section):
        self.ip = None
        self.port = None
        self.host = None

        self.name = section.name
        self.queue = section.queue
        self.concurrent_limit = section.concurrent_limit
        self.retry_max_count = section.retry_max_count

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
