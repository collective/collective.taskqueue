# -*- coding: utf-8 -*-
from Acquisition import aq_base
from zope.component import getUtility
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.PluggableAuthService.interfaces.plugins import (
    IExtractionPlugin,
    IAuthenticationPlugin
)
from Products.PlonePAS.Extensions.Install import activatePluginInterfaces
from AccessControl.Permissions import add_user_folders
from Products.PluggableAuthService import PluggableAuthService

from collective.taskqueue.pasplugin import taskauthplugin

PluggableAuthService.registerMultiPlugin(
    taskauthplugin.TaskQueueAuthPlugin.meta_type
)


def initialize(context):
    context.registerClass(
        taskauthplugin.TaskQueueAuthPlugin,
        permission=add_user_folders,
        constructors=(
            taskauthplugin.manage_addTaskQueueAuthPluginForm,
            taskauthplugin.manage_addTaskQueueAuthPlugin
        ),
        visibility=None
    )


def configureTaskQueueAuthPlugin(context):
    if context.readDataFile("collective.taskqueue.taskauth.txt") is None:
        return  # not our profile

    site = getUtility(ISiteRoot)
    pas = getToolByName(site, "acl_users")

    if "taskauth" not in pas.objectIds():
        factory = pas.manage_addProduct["collective.taskqueue.pasplugin"]
        factory.manage_addTaskQueueAuthPlugin(
            "taskauth",
            "Task Queue PAS plugin"
        )

    activatePluginInterfaces(site, "taskauth")

    # Make plugin the first one in order:
    try:
        for i in range(len(pas.plugins.listPluginIds(IExtractionPlugin))):
            pas.plugins.movePluginsUp(IExtractionPlugin, ("taskauth",))
    except:
        pass
    try:
        for i in range(len(pas.plugins.listPluginIds(IAuthenticationPlugin))):
            pas.plugins.movePluginsUp(IAuthenticationPlugin, ("taskauth",))
    except:
        pass
