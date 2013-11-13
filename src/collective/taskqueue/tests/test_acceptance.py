# -*- coding: utf-8 -*-
import unittest
from Products.CMFCore.utils import getToolByName

from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
import robotsuite
from plone.testing import layered, z2
from zope import schema
from zope.configuration import xmlconfig
from zope.interface import Interface
from z3c.form import form, field, button

from collective.taskqueue import taskqueue
from collective.taskqueue.testing import TASK_QUEUE_ZSERVER_FIXTURE, REDIS_TASK_QUEUE_ZSERVER_FIXTURE, ZSERVER_FIXTURE


class TaskQueueFormLayer(PloneSandboxLayer):
    bases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        #import collective.taskqueue.pasplugin
        #xmlconfig.file('configure.zcml',
        #               collective.taskqueue.pasplugin,
        #               context=configurationContext)
        #z2.installProduct(app, 'collective.taskqueue.pasplugin')

        import collective.taskqueue.tests
        xmlconfig.file('test_acceptance.zcml',
                       collective.taskqueue.tests,
                       context=configurationContext)


    def setUpPloneSite(self, portal):
        portal.portal_workflow.setDefaultChain(
            'simple_publication_workflow')
        #self.applyProfile(portal, 'collective.taskqueue.pasplugin:default')


TASK_QUEUE_FORM_FIXTURE = TaskQueueFormLayer()


TASK_QUEUE_ROBOT_TESTING = z2.FunctionalTesting(
    bases=(TASK_QUEUE_ZSERVER_FIXTURE,
           TASK_QUEUE_FORM_FIXTURE,
           REMOTE_LIBRARY_BUNDLE_FIXTURE,
           ZSERVER_FIXTURE),
    name='TaskQueue:Robot')

REDIS_TASK_QUEUE_ROBOT_TESTING = z2.FunctionalTesting(
    bases=(REDIS_TASK_QUEUE_ZSERVER_FIXTURE,
           TASK_QUEUE_FORM_FIXTURE,
           REMOTE_LIBRARY_BUNDLE_FIXTURE,
           ZSERVER_FIXTURE),
    name='RedisTaskQueue:Robot')


class ITaskQueueForm(Interface):

    url = schema.ASCIILine(title=u"Path")


class TaskQueueForm(form.Form):

    fields = field.Fields(ITaskQueueForm)

    ignoreContext = True

    @button.buttonAndHandler(u"Queue")
    def handleQueue(self, action):
        data, errors = self.extractData()
        if errors:
            return False
        taskqueue.add(data.get('url'))
        plone_utils = getToolByName(self.context, 'plone_utils')
        plone_utils.addPortalMessage("Queued a new request")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([
        layered(robotsuite.RobotTestSuite('test_acceptance.robot'),
                layer=TASK_QUEUE_ROBOT_TESTING),
    ])
    suite.addTests([
        layered(robotsuite.RobotTestSuite('test_acceptance.robot'),
                layer=REDIS_TASK_QUEUE_ROBOT_TESTING),
    ])
    return suite
