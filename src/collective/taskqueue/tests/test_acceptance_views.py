# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from collective.taskqueue import taskqueue
from z3c.form import button
from z3c.form import field
from z3c.form import form
from zope import schema
from zope.interface import Interface


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
        _authenticator = self.request.form.get("_authenticator")
        if not _authenticator:
            taskqueue.add(data.get("url"))
        else:
            taskqueue.add(data.get("url"), params={"_authenticator": _authenticator})
        plone_utils = getToolByName(self.context, "plone_utils")
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
        path = "/".join(self.context.getPhysicalPath())
        for i in range(data["amount"]):
            taskqueue.add("{0:s}/send-email-view".format(path), method="POST")
        plone_utils = getToolByName(self.context, "plone_utils")
        plone_utils.addPortalMessage("Queued {0:d} new email(s)".format(data["amount"]))


class TaskQueueEmailView(BrowserView):
    def __call__(self):
        mailhost = getToolByName(self.context, "MailHost")
        mailhost.send(
            self.request.form.get("form.widgets.message"),
            mto="recipient@localhost",
            mfrom="sender@localhost",
            subject="Test Email",
            charset="utf-8",
        )
        return u"Ok."
