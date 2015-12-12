# -*- coding: utf-8 -*-

import pkg_resources

try:
    pkg_resources.get_distribution('redis')
except pkg_resources.DistributionNotFound:
    HAS_REDIS = False
else:
    HAS_REDIS = True

try:
    pkg_resources.get_distribution('msgpack-python')
except pkg_resources.DistributionNotFound:
    HAS_MSGPACK = False
else:
    HAS_MSGPACK = True

HAVE_PLONE_5 = \
    int(pkg_resources.get_distribution('Products.CMFPlone').version[0]) > 4

TASK_QUEUE_IDENT = 'TaskQueue'
TASK_QUEUE_SERVER_IDENT = 'TaskQueueServer'
