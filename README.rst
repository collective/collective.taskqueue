collective.taskqueue
====================

Yet another way to dispatch and execute asynchronous tasks in Plone.

**This is an experiment. Not battle tested.**

*collective.taskqueue* provides asynchronous tasks by providing small
a framework for queueing asynchronously processed requests for ZPublisher.
While this cannot be the most performance wise way to implement asynchronous
tasks for Plone, it's easy to use, because asynchronous tasks are just normal
calls to normally registered browser views (or other traversable callables).

Minimal configuration:

.. code:: ini

   zope-conf-additional =
       %import collective.taskqueue
       <taskqueue-server>
       </taskqueue-server>

Minimal Redis configuration:

.. code:: ini

   eggs =
       collective.taskqueue[redis]

   zope-conf-additional =
       %import collective.taskqueue
       <product-config collective.taskqueue>
         queue redis
         redis_unixsocket ${buildout:directory}/var/redis.sock
       </product-config>
       <taskqueue-server>
         queue redis
       </taskqueue-server>


