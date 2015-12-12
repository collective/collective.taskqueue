# -*- coding: utf-8 -*-
import unittest
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView

from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.robotframework.testing import MOCK_MAILHOST_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
import robotsuite
from plone.testing import layered, z2
from zope import schema
from zope.configuration import xmlconfig
from zope.interface import Interface
from z3c.form import form, field, button

from collective.taskqueue import taskqueue
from collective.taskqueue.config import HAS_REDIS
from collective.taskqueue.config import HAS_MSGPACK
from collective.taskqueue.config import HAVE_PLONE_5
from collective.taskqueue.testing import TASK_QUEUE_ZSERVER_FIXTURE
from collective.taskqueue.testing import REDIS_TASK_QUEUE_ZSERVER_FIXTURE
from collective.taskqueue.testing import ZSERVER_FIXTURE


class TaskQueueFormLayer(PloneSandboxLayer):
    bases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        #import collective.taskqueue.pasplugin
        #xmlconfig.file('configure.zcml',
        #               collective.taskqueue.pasplugin,
        #               context=configurationContext)
        #z2.installProduct(app, 'collective.taskqueue.pasplugin')

        if HAVE_PLONE_5:
            import plone.app.contenttypes
            xmlconfig.file('configure.zcml',
                           plone.app.contenttypes,
                           context=configurationContext)

        import collective.taskqueue.tests
        xmlconfig.file('test_acceptance.zcml',
                       collective.taskqueue.tests,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        portal.portal_workflow.setDefaultChain(
            'simple_publication_workflow')
        if HAVE_PLONE_5:
            self.applyProfile(portal, 'plone.app.contenttypes:default')
        #self.applyProfile(portal, 'collective.taskqueue.pasplugin:default')

TASK_QUEUE_FORM_FIXTURE = TaskQueueFormLayer()


TASK_QUEUE_ROBOT_TESTING = z2.FunctionalTesting(
    bases=(TASK_QUEUE_ZSERVER_FIXTURE,
           MOCK_MAILHOST_FIXTURE,
           REMOTE_LIBRARY_BUNDLE_FIXTURE,
           TASK_QUEUE_FORM_FIXTURE,
           ZSERVER_FIXTURE),
    name='TaskQueue:Robot')

REDIS_TASK_QUEUE_ROBOT_TESTING = z2.FunctionalTesting(
    bases=(REDIS_TASK_QUEUE_ZSERVER_FIXTURE,
           MOCK_MAILHOST_FIXTURE,
           REMOTE_LIBRARY_BUNDLE_FIXTURE,
           TASK_QUEUE_FORM_FIXTURE,
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
        _authenticator = self.request.form.get('_authenticator')
        if not _authenticator:
            taskqueue.add(data.get('url'))
        else:
            taskqueue.add(data.get('url'),
                          params={'_authenticator': _authenticator})
        plone_utils = getToolByName(self.context, 'plone_utils')
        plone_utils.addPortalMessage("Queued a new request")


class ITaskQueueEmailForm(Interface):

    message = schema.TextLine(title=u"Message")
    amount = schema.Int(title=u"Amount")


class TaskQueueEmailForm(form.Form):

    fields = field.Fields(ITaskQueueEmailForm)

    ignoreContext = True

    @button.buttonAndHandler(u"Queue")
    def handleQueue(self, action):
        data, errors = self.extractData()
        if errors:
            return False
        path = '/'.join(self.context.getPhysicalPath())
        for i in range(data['amount']):
            taskqueue.add('/{0:s}/send-email-view'.format(path), method='POST')
        plone_utils = getToolByName(self.context, 'plone_utils')
        plone_utils.addPortalMessage(
            "Queued {0:d} new email(s)".format(data['amount']))


class TaskQueueEmailView(BrowserView):

    def __call__(self):
        mailhost = getToolByName(self.context, 'MailHost')
        mailhost.send(
            self.request.form.get('form.widgets.message'),
            'recipient@localhost',
            'sender@localhost',
            "Test Email"
        )
        return u"Ok."


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([
        layered(robotsuite.RobotTestSuite('test_acceptance.robot'),
                layer=TASK_QUEUE_ROBOT_TESTING),
    ])
    if HAS_REDIS and HAS_MSGPACK:
        suite.addTests([
            layered(robotsuite.RobotTestSuite('test_acceptance.robot'),
                    layer=REDIS_TASK_QUEUE_ROBOT_TESTING),
        ])
    return suite
