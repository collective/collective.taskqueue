# -*- coding: utf-8 -*-
from zope.interface import Interface
from zope.interface import Attribute


class ITaskQueue(Interface):

    name = Attribute("Queue name")

    def __len__():
        """Return current length of the queue"""

    def add(url, method, params, headers, payload):
        """Create task and queue it after successful transaction"""

    def put(task):
        """Put task into queue"""

    def get():
        """Get task from queue"""

    def task_done():
        """Acknowledge the last got task done"""


class ITaskQueueLayer(Interface):
    """Marker interface for TaskQueue requests"""

