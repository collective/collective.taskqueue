from collective.taskqueue.redisqueue import RedisTaskQueue as redis
from collective.taskqueue.taskqueue import LocalVolatileTaskQueue as local


assert local
assert redis
