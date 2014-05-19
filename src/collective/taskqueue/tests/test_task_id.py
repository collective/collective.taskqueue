# -*- coding: utf-8 -*-
import Queue
import logging
import unittest

from plone.testing import z2
import transaction
from zope.component import getUtility
from zope.testing.loggingsupport import InstalledHandler

from collective.taskqueue import taskqueue
from collective.taskqueue.interfaces import ITaskQueue
from collective.taskqueue.testing import (
    LocalTaskQueueServerLayer,
    runAsyncTest
)


logger = logging.getLogger('collective.taskqueue')


class TaskIdLoggingTaskQueueServerLayer(LocalTaskQueueServerLayer):

    def setUp(self):
        super(TaskIdLoggingTaskQueueServerLayer, self).setUp()

        def logging_handler(app, request, response):
            logger.info(request.getHeader("X-Task-Id"))
            response.stdout.write('HTTP/1.1 204\r\n')
            response.stdout.close()

        self['server'].handler = logging_handler


TASK_QUEUE_FIXTURE = TaskIdLoggingTaskQueueServerLayer(queue='test-queue')

TASK_QUEUE_FUNCTIONAL_TESTING = z2.FunctionalTesting(
    bases=(TASK_QUEUE_FIXTURE,),
    name='TaskQueue:Functional')


class TestLocalVolatileTaskQueue(unittest.TestCase):

    layer = TASK_QUEUE_FUNCTIONAL_TESTING
    queue = 'test-queue'

    @property
    def task_queue(self):
        return getUtility(ITaskQueue, name=self.queue)

    def setUp(self):
        self.task_queue.queue = Queue.Queue()

    def _testConsumeFromQueue(self):
        self.assertEqual(len(self.task_queue), 0)

    def testTaskId(self):
        self.assertEqual(len(self.task_queue), 0)
        a = taskqueue.add("/", queue=self.queue)
        b = taskqueue.add("/Plone", queue=self.queue)
        transaction.commit()
        self.assertEqual(len(self.task_queue), 2)

        handler = InstalledHandler("collective.taskqueue")
        runAsyncTest(self._testConsumeFromQueue)
        messages = [record.getMessage() for record in handler.records]
        self.assertEqual(messages[-2:], [a, b])

