from collective.taskqueue.config import HAS_MSGPACK
from collective.taskqueue.config import HAVE_PLONE_5
from collective.taskqueue.testing import REDIS_TASK_QUEUE_ZSERVER_FIXTURE
from collective.taskqueue.testing import TASK_QUEUE_ZSERVER_FIXTURE
from collective.taskqueue.testing import ZSERVER_FIXTURE
from plone.app.robotframework.testing import MOCK_MAILHOST_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing import layered
from plone.testing import z2
from zope.configuration import xmlconfig

import robotsuite
import unittest


class TaskQueueFormLayer(PloneSandboxLayer):
    bases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # import collective.taskqueue.pasplugin
        # xmlconfig.file('configure.zcml',
        #               collective.taskqueue.pasplugin,
        #               context=configurationContext)
        # z2.installProduct(app, 'collective.taskqueue.pasplugin')

        if HAVE_PLONE_5:
            import plone.app.contenttypes

            xmlconfig.file(
                "configure.zcml", plone.app.contenttypes, context=configurationContext
            )

        import collective.taskqueue.tests

        xmlconfig.file(
            "test_acceptance.zcml",
            collective.taskqueue.tests,
            context=configurationContext,
        )

    def setUpPloneSite(self, portal):
        portal.portal_workflow.setDefaultChain("simple_publication_workflow")
        if HAVE_PLONE_5:
            self.applyProfile(portal, "plone.app.contenttypes:default")
        # self.applyProfile(portal, 'collective.taskqueue.pasplugin:default')


TASK_QUEUE_FORM_FIXTURE = TaskQueueFormLayer()


TASK_QUEUE_ROBOT_TESTING = z2.FunctionalTesting(
    bases=(
        TASK_QUEUE_ZSERVER_FIXTURE,
        MOCK_MAILHOST_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        TASK_QUEUE_FORM_FIXTURE,
        ZSERVER_FIXTURE,
    ),
    name="TaskQueue:Robot",
)

REDIS_TASK_QUEUE_ROBOT_TESTING = z2.FunctionalTesting(
    bases=(
        REDIS_TASK_QUEUE_ZSERVER_FIXTURE,
        MOCK_MAILHOST_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        TASK_QUEUE_FORM_FIXTURE,
        ZSERVER_FIXTURE,
    ),
    name="RedisTaskQueue:Robot",
)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(
        [
            layered(
                robotsuite.RobotTestSuite("test_acceptance.robot"),
                layer=TASK_QUEUE_ROBOT_TESTING,
            )
        ]
    )
    if HAS_MSGPACK:
        suite.addTests(
            [
                layered(
                    robotsuite.RobotTestSuite("test_acceptance.robot"),
                    layer=REDIS_TASK_QUEUE_ROBOT_TESTING,
                )
            ]
        )
    return suite
