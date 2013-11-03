collective.taskqueue
====================

.. image:: https://secure.travis-ci.org/datakurre/collective.taskqueue.png
   :target: http://travis-ci.org/datakurre/collective.taskqueue

Yet another way to dispatch and execute asynchronous tasks in Plone.

**This is an experiment. Not yet battle tested.**

*collective.taskqueue* enables asynchronous tasks in Plone add-ons by
providing a small framework for asynchronously queueing requests for
ZPublisher. Even this design does not the best performance for your
asynchronous Plone tasks, it should be quite easy to use: asynchronous tasks
are just normal calls to normally registered browser views (or other
traversable callables) and they authenticated using PAS as all the other
requests.

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

Usage:

.. code:: python

   from collective.taskqueue import taskqueue
   taskqueue.add('/Plone/path/to/my/view')

Tasks are queued (and consumed) after a successful transaction.

By default, ``taskqueue.add`` copies headers from the current requests to the
asynchronous request. That should be enough to authenticate the requests as the
same way as the current request was authenticated. Alternative authentication
can be implemented with a custom PAS-plugin and passing custom
headers-dictionary (like ``headers={...}`` for ``taskqueue.add``).
