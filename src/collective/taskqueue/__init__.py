# -*- coding: utf-8 -*-
from collective.taskqueue.config import HAS_MSGPACK
from collective.taskqueue.config import HAS_REDIS
from collective.taskqueue.taskqueue import LocalVolatileTaskQueue as local


if HAS_REDIS and HAS_MSGPACK:
    from collective.taskqueue.redisqueue import RedisTaskQueue as redis
