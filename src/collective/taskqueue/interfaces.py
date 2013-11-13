# -*- coding: utf-8 -*-
from zope.interface import Interface
from zope.interface import Attribute


class ITaskQueue(Interface):

    name = Attribute("Queue registration name (readonly)")

    def __len__():
        """Return current length of the queue excluding currently processed
        messages; Positive length does not guarantee that the next get()
        returns a value.
        """

    def add(url, method, params, headers, payload):
        """Create task and queue it after successful transaction"""

    def put(task):
        """Put task into queue; Called by transaction data manager"""

    def get(consumer_name):
        """Get task from queue; Called by task queue server; May return None"""

    def task_done(task, status_line, consumer_name, consumer_length):
        """Acknowledge the task done; Called by task queue server"""

    def reset():
        """Reset task queue"""


class ITaskQueueLayer(Interface):
    """Marker interface for task queue server dispatched requests; Can be used
    to configure views only visible for queued tasks.
    """
