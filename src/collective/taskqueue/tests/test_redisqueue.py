# -*- coding: utf-8 -*-

from collective.taskqueue.config import HAS_REDIS
from collective.taskqueue.config import HAS_MSGPACK
from collective.taskqueue.testing import REDIS_TASK_QUEUE_FUNCTIONAL_TESTING
from collective.taskqueue.tests.test_taskqueue import\
    TestLocalVolatileTaskQueue


if HAS_REDIS and HAS_MSGPACK:

    class TestRedisTaskQueue(TestLocalVolatileTaskQueue):

        layer = REDIS_TASK_QUEUE_FUNCTIONAL_TESTING
        queue = 'test-queue'

        def setUp(self):
            while len(self.task_queue):
                task = self.task_queue.get(consumer_name='default')
                self.task_queue.task_done(
                    task, status_line='HTTP/1.1 200',
                    consumer_name='default', consumer_length=0)
