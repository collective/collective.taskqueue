# -*- coding: utf-8 -*-
import asyncore
import logging
import socket
from App.config import getConfiguration

from zope.configuration import xmlconfig

from plone.testing import Layer
from plone.testing import z2
from collective.taskqueue import taskqueue

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


class ZServer(z2.ZServer):
    """Custom ZServer, which can survive when socket_map is modified between
    different test cases within the same layer"""
    def runner(self):
        socket_map = asyncore.socket_map
        while socket_map and not self._shutdown:
            try:
                asyncore.poll(self.timeout, socket_map)
            except:
                # Try once more, because the socket_map have been modified:
                asyncore.poll(self.timeout, socket_map)

ZSERVER_FIXTURE = ZServer()


class TaskQueueServerLayer(Layer):
    defaultBases = (z2.STARTUP,)

    def __init__(self, queue='test-queue', zserver_enabled=False):
        super(TaskQueueServerLayer, self).__init__()
        self.queue = queue
        self.zserver_enabled = zserver_enabled

    def setUp(self):
        import collective.taskqueue
        xmlconfig.file('configure.zcml', collective.taskqueue,
                       context=self['configurationContext'])

        # Configure
        config = getConfiguration()
        config.product_config = {'collective.taskqueue': {'queue': self.queue}}
        taskqueue.reset()

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
            self['server'] = TaskQueueServer(queue=self.queue,
                                             handler=logging_handler)
        else:
            self['server'] = TaskQueueServer(queue=self.queue,
                                             handler=zserver_handler,
                                             concurrent_limit=0)
            # concurrent_limit=0, because of limitations in z2.ZServer

    def tearDown(self):
        self['server'].handle_close(force=True)

    def testTearDown(self):
        taskqueue.reset()


class LocalTaskQueueServerLayer(TaskQueueServerLayer):

    def setUp(self):
        import collective.taskqueue.tests
        xmlconfig.file('test_taskqueue.zcml', collective.taskqueue.tests,
                       context=self['configurationContext'])
        super(LocalTaskQueueServerLayer, self).setUp()

TASK_QUEUE_FIXTURE = LocalTaskQueueServerLayer()
TASK_QUEUE_ZSERVER_FIXTURE = LocalTaskQueueServerLayer(zserver_enabled=True)

TASK_QUEUE_INTEGRATION_TESTING = z2.IntegrationTesting(
    bases=(TASK_QUEUE_FIXTURE,),
    name='TaskQueue:Integration')

TASK_QUEUE_FUNCTIONAL_TESTING = z2.FunctionalTesting(
    bases=(TASK_QUEUE_FIXTURE,),
    name='TaskQueue:Functional')


class RedisTaskQueueServerLayer(TaskQueueServerLayer):

    def setUp(self):
        import collective.taskqueue.tests
        xmlconfig.file('test_redisqueue.zcml', collective.taskqueue.tests,
                       context=self['configurationContext'])
        super(RedisTaskQueueServerLayer, self).setUp()

REDIS_TASK_QUEUE_FIXTURE = RedisTaskQueueServerLayer()
REDIS_TASK_QUEUE_ZSERVER_FIXTURE =\
    RedisTaskQueueServerLayer(zserver_enabled=True)

REDIS_TASK_QUEUE_INTEGRATION_TESTING = z2.IntegrationTesting(
    bases=(REDIS_TASK_QUEUE_FIXTURE,),
    name='RedisTaskQueue:Integration')

REDIS_TASK_QUEUE_FUNCTIONAL_TESTING = z2.FunctionalTesting(
    bases=(REDIS_TASK_QUEUE_FIXTURE,),
    name='RedisTaskQueue:Functional')
