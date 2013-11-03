# -*- coding: utf-8 -*-
from zope import schema
from zope.interface import Interface
from z3c.form import form, field, button

from collective.taskqueue import taskqueue


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
        for i in range(1):
            taskqueue.add(data.get('url'))
