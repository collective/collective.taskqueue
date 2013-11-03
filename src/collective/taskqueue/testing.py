# -*- coding: utf-8 -*-
import Queue
import asyncore
import logging
from zope.component import getUtility

from zope.configuration import xmlconfig

from plone.testing import Layer
from plone.testing import z2
from collective.taskqueue.interfaces import ITaskQueue

logger = logging.getLogger('collective.taskqueue')


def runAsyncTest(testMethod, timeout=100, loop_timeout=0.1, loop_count=1):
    """Helper method for running tests requiring asyncore loop"""
    while True:
        try:
            asyncore.loop(timeout=loop_timeout, count=loop_count)
            return testMethod()
        except AssertionError:
            if timeout > 0:
                timeout -= 1
                continue
            else:
                raise


class TaskQueueServerLayer(Layer):
    defaultBases = (z2.STARTUP,)

    def __init__(self, zserver_enabled=False):
        super(TaskQueueServerLayer, self).__init__()
        self.zserver_enabled = zserver_enabled
        self.server = None

    def setUp(self):
        # Configure
        import collective.taskqueue
        xmlconfig.file('configure.zcml', collective.taskqueue,
                       context=self['configurationContext'])

        # Define logging request handler to replace ZPublisher
        def logging_handler(app, request, response):
            logger.info(request.getURL() + request.get("PATH_INFO"))
            response.stdout.write('HTTP/1.1 204\r\n')
            response.stdout.close()

        # Define ZPublisher-based request handler to be used with zserver
        def zserver_handler(app, request, response):
            from ZPublisher import publish_module
            publish_module(app, request=request, response=response)

        # Create TaskQueueServer
        from collective.taskqueue.server import TaskQueueServer
        if not self.zserver_enabled:
            self.server = TaskQueueServer(handler=logging_handler)
        else:
            self.server = TaskQueueServer(handler=zserver_handler)

    def testSetUp(self):
        # Reset queue
        task_queue = getUtility(ITaskQueue, name="default")
        task_queue.queue = Queue.Queue()

TASK_QUEUE_FIXTURE = TaskQueueServerLayer()
TASK_QUEUE_ZSERVER_FIXTURE = TaskQueueServerLayer()


TASK_QUEUE_INTEGRATION_TESTING = z2.IntegrationTesting(
    bases=(TASK_QUEUE_FIXTURE,),
    name='TaskQueue:Integration')

TASK_QUEUE_FUNCTIONAL_TESTING = z2.FunctionalTesting(
    bases=(TASK_QUEUE_FIXTURE,),
    name='TaskQueue:Functional')