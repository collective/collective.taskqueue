collective.taskqueue
====================

Minimal configuration:

.. code:: ini

   zope-conf-additional =
       %import collective.taskqueue
       <taskqueue-server>
       </taskqueue-server>

Minimal Redis configuration:

.. code:: ini

   zope-conf-additional =
       %import collective.taskqueue
       <product-config collective.taskqueue>
         queue redis
         redis_unixsocket ${buildout:directory}/var/redis.sock
       </product-config>
       <taskqueue-server>
         queue redis
       </taskqueue-server>


