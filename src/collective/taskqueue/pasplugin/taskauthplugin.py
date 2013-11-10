# -*- coding: utf-8 -*-
from AccessControl.SecurityInfo import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces.plugins import (
    IExtractionPlugin,
    IAuthenticationPlugin
)

from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements

from collective.taskqueue.interfaces import ITaskQueueLayer

manage_addTaskQueueAuthPluginForm =\
    PageTemplateFile('taskauthplugin', globals(),
                     __name__='manage_addTaskQueueAuthPluginForm')


def manage_addTaskQueueAuthPlugin(dispatcher, id, title=None, REQUEST=None):
    """Add a Task Queue Auth Plugin"""
    sp = TaskQueueAuthPlugin(id, title=title)
    dispatcher._setObject(id, sp)

    if REQUEST is not None:
        REQUEST.response.redirect(
            '%s/manage_workspace?'
            'manage_tabs_message=TaskQueue+PAS+plugin+created.' %
            dispatcher.absolute_url()
        )


class TaskQueueAuthPlugin(BasePlugin):
    meta_type = 'Task Queue Auth Plugin'
    security = ClassSecurityInfo()

    def __init__(self, id, title=None):
        self._setId(id)
        self.title = title

    # IExtractionPlugin implementation
    def extractCredentials(self, request):
        # Check if request provides ITaskQueueLayer
        if not ITaskQueueLayer.providedBy(request):
            return {}

        # Read magical header
        task_user_id = request.getHeader('X-Task-User-Id')
        if task_user_id != None:
            return {'login': task_user_id}

        return {}

    # IAuthenticationPlugin implementation
    def authenticateCredentials(self, credentials):
        # Verity credentials source
        if credentials.get('extractor') != self.getId():
            return None

        # Verify credentials data
        if not 'login' in credentials:
            return None

        # Verify user
        pas = self._getPAS()
        info = pas._verifyUser(
            pas.plugins, user_id=credentials['login'])

        if info is None:
            return None

        # Let the task request in as requested user
        return info['id'], info['login']

classImplements(TaskQueueAuthPlugin, IExtractionPlugin, IAuthenticationPlugin)
InitializeClass(TaskQueueAuthPlugin)
