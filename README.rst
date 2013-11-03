collective.taskqueue
====================

.. image:: https://secure.travis-ci.org/datakurre/collective.taskqueue.png
   :target: http://travis-ci.org/datakurre/collective.taskqueue

Yet another way to dispatch and execute asynchronous tasks in Plone.

**This is an experiment. Not battle tested.**

*collective.taskqueue* enables asynchronous tasks in Plone by providing a
small framework for queueing asynchronously processed requests for ZPublisher.
While this cannot be the most performance wise way to implement asynchronous
tasks for Plone, it's easy to use, because asynchronous tasks are just normal
calls to normally registered browser views (or other traversable callables).

Minimal configuration:

.. code:: ini

   zope-conf-additional =
       %import collective.taskqueue
       <taskqueue-server>
       </taskqueue-server>

Example Redis configuration:

.. code:: ini

   eggs =
       collective.taskqueue[redis]

   zope-conf-additional =
       %import collective.taskqueue
       <product-config collective.taskqueue>
         queue redis
         redis_unix_socket_path ${buildout:directory}/var/redis.sock
       </product-config>
       <taskqueue-server>
         name ${:_buildout_section_name_}
         queue redis
       </taskqueue-server>
