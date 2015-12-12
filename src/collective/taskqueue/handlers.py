# -*- coding: utf-8 -*-

from Products.CMFCore.utils import getToolByName

from collective.taskqueue.interfaces import ITaskQueueLayer


def setLanguageBindings(site, event):
    # Fixes issue where language bindings are not set, because language tool
    # check explicitly for HTTPRequest, which TaskQueueRequest only inherits.
    # Note: Plone >= 5 no longer has LanguageTool and this is not required.
    request = getattr(event, 'request', None)
    if not ITaskQueueLayer.providedBy(request):
        return
    portal_languages = getToolByName(site, 'portal_languages')
    portal_languages.setLanguageBindings()
