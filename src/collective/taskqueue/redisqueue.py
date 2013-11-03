# -*- coding: utf-8 -*-
import msgpack

from plone.memoize import forever
from zope.interface import implements
import redis

from collective.taskqueue.interfaces import ITaskQueue
from collective.taskqueue.taskqueue import TaskQueueBase
from collective.taskqueue.taskqueue import TaskQueueTransactionDataManager
from collective.taskqueue.taskqueue import get_setting


class RedisTaskQueueTDM(TaskQueueTransactionDataManager):

    def tpc_vote(self, t):
        # Vote 'no' by raising ConnectionError when Redis is down to abort
        # the transaction with queued tasks.
        self.queue.redis.ping()


class RedisTaskQueue(TaskQueueBase):

    implements(ITaskQueue)

    transaction_data_manager = RedisTaskQueueTDM

    def __init__(self):
        unixsocket = get_setting('redis_unixsocket', None)
        assert unixsocket, """\
Redis configuration not found. Do you have

<product-config collective.taskqueue>
    redis_unixsocket /path/to/redis.sock
</product-config>

in your zope.conf?
"""
        self.redis = redis.StrictRedis(unix_socket_path=unixsocket)
        self._requeued_processing = False  # Requeue old processing on start

    @property
    @forever.memoize
    def redis_key(self):
        return 'collective.taskqueue.{0:s}'.format(self.name)

    def __len__(self):
        try:
            return int(self.redis.llen(self.redis_key))
        except redis.ConnectionError:
            return 0

    def serialize(self, task):
        return msgpack.dumps(sorted(task.items()))

    def deserialize(self, msg):
        if msg is not None:
            return dict(msgpack.loads(msg))
        else:
            return None

    def put(self, task):
        self.redis.lpush(self.redis_key, self.serialize(task))

    def get(self, consumer_name):
        consumer_key = '{0:s}.{1:s}'.format(self.redis_key, consumer_name)

        if not self._requeued_processing:
            self._requeue_processing(consumer_name)
        try:
            msg = self.redis.rpoplpush(self.redis_key, consumer_key)
        except redis.ConnectionError:
            msg = None
        return self.deserialize(msg)

    def task_done(self, task, status_line, consumer_name, consumer_length):
        consumer_key = '{0:s}.{1:s}'.format(self.redis_key, consumer_name)

        self.redis.lrem(consumer_key, -1, self.serialize(task))
        if consumer_length == 0:
            self._requeue_processing(consumer_name)

    def _requeue_processing(self, consumer_name):
        consumer_key = '{0:s}.{1:s}'.format(self.redis_key, consumer_name)

        try:
            while self.redis.llen(consumer_key) > 0:
                self.redis.rpoplpush(consumer_key, self.redis_key)
            self._requeued_processing = True
        except redis.ConnectionError:
            pass
