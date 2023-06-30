# flake8: noqa because this is temporary

# Rationale:
#
# - Zope nowadays runs behind WSGI
# - Modern (web) applications might want to serve websockets
# - Tools utilizing asyncio are a common thing and some might want to use them
# - Having twisted and/or asyncio opens a new universe of computing next to serving a web application inside one process
#
# Discussion:
#
# - Any discussion about why to use twisted is pointless.
# - It's there, it works, it's maintained, it's (API) stable.
#
# So, let's head over to the interesting part.
#
# Install required python packages with pip:
#
#     pip install twisted plaster plaster_pastedeploy
#
# Start twisted:
#
#     twistd -ny zope.tac

# `twistd` needs an application config file, or `*.tac` file to run.
# It is a python file and the main purpose is to instantiate the `application`
# So the entire code below can be moved to a dedicated python package/module
# as long as there ends up an `Application` instance named after `application`
# in this file.

# install asyncio main loop in twisted
from twisted.internet import asyncioreactor


asyncioreactor.install()

from collections import namedtuple
from collective.taskqueue.datatypes import TaskQueueFactory
from collective.taskqueue.datatypes import TaskQueueServerFactory
from twisted.application import internet
from twisted.application import service
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

import os
import plaster


config = "parts/instance/etc/wsgi.ini"
config = os.path.abspath(config)
port = 8081

# Create the WSGI application
loader = plaster.get_loader(config, protocols=["wsgi"])
app = loader.get_wsgi_app("main")

# Twisted WSGI server setup
resource = WSGIResource(reactor, reactor.getThreadPool(), app)
factory = Site(resource)

# Twisted Application setup
application = service.Application("zope")
internet.TCPServer(port, factory).setServiceParent(application)


# Task Queue
task_queue = (
    TaskQueueFactory(
        namedtuple(
            "TaskQueueSection",
            ["queue", "type", "host", "port", "db", "password", "unix_socket_path"],
        )(
            queue="default",
            type="collective.taskqueue.redisqueue.RedisTaskQueue",
            host="localhost",
            port=6379,
            db=1,
            password="",
            unix_socket_path="",
        )
    )
    .create()
    .setServiceParent(application)
)

# Task Queue Worker
server = (
    TaskQueueServerFactory(
        namedtuple(
            "TaskQueueServerSection",
            ["name", "queue", "concurrent_limit", "retry_max_count"],
        )(
            name="default",
            queue="default",
            concurrent_limit=1,
            retry_max_count=10,
        )
    )
    .create()
    .setServiceParent(application)
)
