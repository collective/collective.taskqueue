collective.taskqueue
====================

.. image:: https://secure.travis-ci.org/collective/collective.taskqueue.png
   :target: http://travis-ci.org/collective/collective.taskqueue

*collective.taskqueue* enables asynchronous tasks in Plone add-ons by
providing a small framework for asynchronously queueing requests to
ZPublisher. With this approach, asynchronous tasks
are just normal calls to normally registered browser views (or other
traversable callables) and they are authenticated using PAS as are all the other
requests.

In addition, it's possible to configure views so that they are visible only for
asynchronous requests. Also, *collective.taskqueue* ships with a special
PAS-plugin, which authenticates each request as the user who queued it.

Minimal configuration:

.. code:: ini

   zope-conf-additional =
       %import collective.taskqueue
       <taskqueue />
       <taskqueue-server />

Minimal configuration gives you one volatile instance-local queue and
consumer, but no guarantee on delivery.

Minimal configuration with multiple queues:

.. code:: ini

   zope-conf-additional =
       %import collective.taskqueue
       <taskqueue />
       <taskqueue-server />

       <taskqueue>
       queue mailhost
       </taskqueue>
       <taskqueue-server>
       queue mailhost
       </taskqueue-server>

Preferred minimal configration with Redis:

.. code:: ini

   eggs =
       collective.taskqueue [redis]

   zope-conf-additional =
       %import collective.taskqueue
       <taskqueue>
         type redis
         unix_socket_path ${buildout:directory}/var/redis.sock
       </taskqueue>
       <taskqueue-server>
         name ${:_buildout_section_name_}
       </taskqueue-server>

Redis-support gives you distributable queues, which can be shared between
instances. All instances should have queue-specific `<taskqueue />`, but only
the consuming instance requires `<taskqueue-server />`.

Example Redis configuration with multiple queues:

.. code:: ini

   eggs =
       collective.taskqueue [redis]

   zope-conf-additional =
       %import collective.taskqueue
       <taskqueue>
         type redis
         unix_socket_path ${buildout:directory}/var/redis.sock
       </taskqueue>
       <taskqueue-server>
         name ${:_buildout_section_name_}
       </taskqueue-server>
       <taskqueue>
         type redis
         queue mailhost
         unix_socket_path ${buildout:directory}/var/redis.sock
       </taskqueue>
       <taskqueue-server>
         queue mailhost
         name ${:_buildout_section_name_}
       </taskqueue-server>

It's recommended to only use local Redis-installations, because remote
connections can be killed by firewalls (there's no ping or heartbeat to keep
the connection alive through enterprise firewalls).

Queue a task:

.. code:: python

   from collective.taskqueue import taskqueue
   task_id = taskqueue.add('/Plone/path/to/my/view')

Tasks are queued (and consumed) after a successful transaction.

To make views visible only for asynchronous requests, views can be registered
for a special layer ``collective.taskqueue.interfaces.ITaskQueueLayer``, which
is only found from requests dispatched by *collective.taskqueue*.

By default, ``taskqueue.add`` copies headers from the current requests to the
asynchronous request. That should be enough to authenticate the requests in
exactly the the same way as the current request was authenticated.

``taskqueue.add`` returns uuid like id for the task, which can be used e.g. to
track the task status later. Task id later provided as ``X-Task-Id`` header in
the queued request. You can get it in your task view with ``self.request.getHeader('X-Task-Id')``.

More robust authentication can be implemented with a custom PAS-plugin.
*collective.taskqueue* ships with an optionally installable PAS-plugin, which
authenticates each request as the user who queued it. To achieve this,
*collective.taskqueue* appends ``X-Task-User-Id``-header into the queued
request.

Taskqueue API has been inspired by `Google AppEngine Task Queue API`__.

__ https://developers.google.com/appengine/docs/python/taskqueue/


Introspecting queues
--------------------

As a minimalistic asynchronous framework for Plone, *collective.taskqueue*
does not provider any user interface for observing or introspecting queues.
Yet, from trusted Python, it is possible to look up a current length of
a named queue (name of the default queue is "default"):

.. code:: python

   from zope.component import getUtility
   from collective.taskqueue.interfaces import ITaskQueue

   len(getUtility(ITaskQueue, name='default'))


Advanced configuration
----------------------

Supported  ``<taskqueue />``-settings are:

``queue`` *(default=default)*
    Unique task queue name.

``type`` *(default=local)*
    Task queue type ('local' or 'redis') or full class path to
    a custom type.

``unix_socket_path``
    Redis server unix socket path (use instead of *host* and *port*).

Other supported Redis-queue options are: *host*, *port*, *db* and *password*.

Supported  ``<taskqueue-server />``-settings are:

``name`` *(default=default)*
    Consumer name, preferably instance name. Consumer is name used by
    Redis-queues for reserving messages from queue to achieve quaranteed
    delivery.

``queue`` *(default=default)*
    Queue name for this consumer (consuming server). There must be a
    ``<taskqueue/>`` with matching *queue*-value registered.

``concurrent_limit`` *(default=1)*
    Maximum concurrent task limit for this consumer. It's recommend to
    set this smaller than *zserver-thread*-count. Leaving this to the
    default (``1``) should give the best results in terms of minimal
    ConflictErrors.

``retry_max_count`` *(default=10)*
    Maximum ZPublisher retry count for requests dispatched by this
    consumer.

    .. note:: Once this limit has been exceeded by ZPublisher, the conflicting
       task is permanently trashed. (An alternative behavior is possible
       by implementing a custom queue class.)


Advanced usage
--------------

``taskqueue.add`` accepts the following arguments (with *default* value):

``url`` *(required, no default)*
  Target path representing the task to be called.

``method`` *(optional, default=GET)*
  HTTP-method for the call. Must be either *GET* or *POST*.

``params`` *(optional, default=None)*
  A dictionary of optional task arguments, which are appended as query string
  after the given *url*.

``headers`` *(optional, default=None)*
  A dictionary of optional HTTP-headers to be appended to (or used to replace)
  the headers copied from the active request.

``payload`` *(optional, default=current)*
  An optional payload for *POST*-request. Payload from the active request
  will be copied by default. Copying the active payload can be prevented
  with *payload=None*.

``queue`` *(optional, default=alphabetically-first-registered-queue)*
  An optional queue name, when more than one queue is registered.


How Redis queueing works
------------------------

1. ``taskqueue.add`` prepares a message, which will be pushed (``lpush``)
   into key ``collective.taskqueue.%(queue)s`` (where ``%(queue)s`` is the
   name of the queue) at the end of the transaction. If Redis connection is
   down during the transaction vote, the whole transaction is aborted.

2. ``<taskqueue-server />`` reads each message (``rpoplpush``) from queue so
   that they will remain in key ``collective.taskqueue.%(queue)s.%(name)s``
   (where ``%(name)s`` is the name of the ``<taskqueue-server/>``) until
   each asynchronous processing request has returned a HTTP response.

3. On startup, and when all known messages have been processed,
   ``<taskqueue-server/>`` purges ``collective.taskqueue.%(queue)s.%(name)s``
   into ``collective.taskqueue.%(queue)s`` (with ``rpoplpush``) and
   those tasks are processed again. (E.g. if Plone was forced to restart
   in middle of task handling request.)

Redis integration uses PubSub to notify itself about new messages in queue
(and get as instant handling as possible in terms of Plone's asyncore-loop).
