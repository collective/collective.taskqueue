# -*- coding: utf-8 -*-
import transaction
import unittest2 as unittest
from zope.component import getUtility
from zope.testing.loggingsupport import InstalledHandler

from collective.taskqueue.interfaces import ITaskQueue
from collective.taskqueue.testing import runAsyncTest
from collective.taskqueue.testing import TASK_QUEUE_FUNCTIONAL_TESTING
from collective.taskqueue import taskqueue


class TestLocalVolatileQueue(unittest.TestCase):

    layer = TASK_QUEUE_FUNCTIONAL_TESTING

    @property
    def task_queue(self):
        return getUtility(ITaskQueue, name="default")

    def testEmptyQueue(self):
        self.assertEqual(len(self.task_queue), 0)

    def testAddToQueue(self):
        taskqueue.add("/")
        self.assertEqual(len(self.task_queue), 0)

    def testCommitToQueue(self):
        taskqueue.add("/")
        self.assertEqual(len(self.task_queue), 0)
        transaction.commit()
        self.assertEqual(len(self.task_queue), 1)
        taskqueue.add("/Plone")
        self.assertEqual(len(self.task_queue), 1)
        transaction.commit()
        self.assertEqual(len(self.task_queue), 2)

    def _testConsumeFromQueue(self):
        self.assertEqual(len(self.task_queue), 0)

    def testConsumeFromQueue(self):
        self.assertEqual(len(self.task_queue), 0)
        taskqueue.add("/")
        taskqueue.add("/Plone")
        transaction.commit()
        self.assertEqual(len(self.task_queue), 2)

        handler = InstalledHandler("collective.taskqueue")
        runAsyncTest(self._testConsumeFromQueue)
        messages = [record.getMessage() for record in handler.records]
        self.assertEqual(messages, ["http://nohost/", "http://nohost/Plone"])
