collective.taskqueue
====================

.. image:: https://secure.travis-ci.org/datakurre/collective.taskqueue.png
   :target: http://travis-ci.org/datakurre/collective.taskqueue

Yet another way to dispatch and execute asynchronous tasks in Plone.

**This is an experiment. Not yet battle tested.**

*collective.taskqueue* enables asynchronous tasks in Plone add-ons by
providing a small framework for asynchronously queueing requests for
ZPublisher. Even this design may not provide the best performance for your
asynchronous Plone tasks, it should be the easiest to use: asynchronous tasks
are just normal calls to normally registered browser views (or other
traversable callables) and they authenticated using PAS as all the other
requests.

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

Example Redis configuration:

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

Example Redis configuration with multiple queues:

.. code:: ini

   eggs =
       collective.taskqueue [redis]

   zope-conf-additional =
       %import collective.taskqueue
       <taskqueue>
         type redis
         unix_socket_path ${buildout:directory}/var/redis.sock
       </product-config>
       <taskqueue-server>
         name ${:_buildout_section_name_}
       </taskqueue-server>
       <taskqueue>
         type redis
         queue mailhost
         unix_socket_path ${buildout:directory}/var/redis.sock
       </product-config>
       <taskqueue-server>
         queue mailhost
         name ${:_buildout_section_name_}
       </taskqueue-server>

Redis-support gives you machine-local queues, which can be shared between
instances. All instances should have `<taskqueue />`, but only the consuming
instance requires `<taskqueue-server />`.

It's recommended to only use local Redis-installations, because remote
connections can be killed by firewalls (there's no ping or heartbeat to keep
the connection alive).

Queue a task:

.. code:: python

   from collective.taskqueue import taskqueue
   taskqueue.add('/Plone/path/to/my/view')

Tasks are queued (and consumed) after a successful transaction.

By default, ``taskqueue.add`` copies headers from the current requests to the
asynchronous request. That should be enough to authenticate the requests as the
same way as the current request was authenticated. More robust authentication
can be implemented with a custom PAS-plugin. (A default one may be shipped
soon with collective.taskqueue...).


Advanced configuration
----------------------

Supported  ``<taskqueue />``-settings are:

``queue`` *(default=default)*
    Unique task queue name.

``type`` *(default=local)*
    Task queue type ('local' or 'redis') or full class path to
    a custom type.

``unix_socket_path``
    Redis server unix socket path (use insetad of *host* and *port*).

Other supported Redis-queue options are:

- *host*
- *port*
- *db*
- *password*

Supported  ``<taskqueue-server />``-settings are:

``name`` *(default=default)*
    Consumer name, preferably instance name. Consumer name can be
    used by queues when reserving messages from broker for processing.

``queue`` *(default=default)*
    Queue name for this consumer (consuming server). There must exist a
    registered utility providing ITaskQueue with this name.

``concurrent_limit`` *(default=1)*
    Maximum concurrent task limit for this consumer. The limit should be
    less than zserver-thread or just 1.

``retry_max_count`` *(default=10)*
    Maximum ZPublisher retry count for requests dispatched by this
    consumer. Once the limit has been exceeded, the conflicting task may
    be permanently skipped, depending the used queue.


Advanced usage
--------------

``taskqueue.add`` accepts the following arguments (with *default* value):

``url`` *(required, no default)*
  Target path representing the task to be called.

``method`` *(optional, default=GET)*
  HTTP-method for the call. Must be either *GET* or *POST*.

``params`` *(optional, default=None)*
  A dictionary of optional task arguments, which are appended as query string
  after the given *url*. (When *params* are provided, *url* must not already
  include any querystring).

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
   into key ``collective.taskqueue.%(queue)s`` (where `%(queue)s`` is the
   name of the queue) at the end of the transaction. If Redis conection is
   done during the transaction vote, the whole transaction is aborted.

2. ``<taskqueue-server />`` reads the message (``rpoplpush``) from queue so
   that it will remain in key ``collective.taskqueue.%(queue)s.%(name)s``
   (where ``%(name)s`` is the name of the ``<taskqueue-server/>``) until
   the asynchronous processing request has returned a HTTP response.

3. On startup and when all known messages have been processed,
   ``<taskqueue-server/>`` purges ``collective.taskqueue.%(queue)s.%(name)s``
   into ``collective.taskqueue.%(queue)s`` (with ``rpoplpush``) and and
   those tasks are processed again.

Redis integration uses PubSub to notify itself of new messages in queue.
