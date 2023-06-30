from App.config import getConfiguration
from collective.taskqueue import txredisapi as redis
from collective.taskqueue.interfaces import ITaskQueue
from collective.taskqueue.taskqueue import TaskQueueBase
from collective.taskqueue.taskqueue import TaskQueueTransactionDataManager
from plone.memoize import forever
from twisted.internet import reactor
from twisted.internet.defer import DeferredLock
from twisted.internet.defer import DeferredQueue
from twisted.internet.defer import inlineCallbacks
from zope.interface import implementer

import msgpack


REDIS_CONNECTION_TIMEOUT = 15


class RedisTaskQueueTDM(TaskQueueTransactionDataManager):
    def tpc_vote(self, t):
        # TODO: Should vote 'no' by raising some exception when Redis is down
        pass


def makeRedisPubSubProtocol(queue):
    class RedisPubSubProtocol(redis.SubscriberProtocol):
        @inlineCallbacks
        def connectionMade(self):
            yield self.subscribe(queue.redis_key)

        @inlineCallbacks
        def messageReceived(self, pattern, channel, message):
            if channel == queue.redis_key and message == "lpush":
                yield queue.messages.put(message)

        def connectionLost(self, reason):
            pass

    return RedisPubSubProtocol


def makeConnection(
    host,
    port,
    dbid,
    poolsize,
    reconnect,
    isLazy,
    charset,
    password,
    connectTimeout,
    replyTimeout,
    convertNumbers,
    protocol=None,
):
    uuid = "%s:%d" % (host, port)
    factory = redis.RedisFactory(
        uuid,
        dbid,
        poolsize,
        isLazy,
        redis.ConnectionHandler,
        charset,
        password,
        replyTimeout,
        convertNumbers,
    )
    factory.continueTrying = reconnect
    if protocol:
        factory.protocol = protocol
    for x in range(poolsize):
        reactor.connectTCP(host, port, factory, connectTimeout)

    if isLazy:
        return factory.handler
    else:
        return factory.deferred


def makeUnixConnection(
    path,
    dbid,
    poolsize,
    reconnect,
    isLazy,
    charset,
    password,
    connectTimeout,
    replyTimeout,
    convertNumbers,
    protocol=None,
):
    factory = redis.RedisFactory(
        path,
        dbid,
        poolsize,
        isLazy,
        redis.UnixConnectionHandler,
        charset,
        password,
        replyTimeout,
        convertNumbers,
    )
    factory.continueTrying = reconnect
    if protocol:
        factory.protocol = protocol
    for x in range(poolsize):
        reactor.connectUNIX(path, factory, connectTimeout)

    if isLazy:
        return factory.handler
    else:
        return factory.deferred


@implementer(ITaskQueue)
class RedisTaskQueue(TaskQueueBase):
    transaction_data_manager = RedisTaskQueueTDM

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.mutex = DeferredLock()
        self.connection = None
        self.messages = DeferredQueue()

    def startService(self):
        promise = self.mutex.acquire()
        promise.addCallback(self._connect)

    @inlineCallbacks
    def _connect(self, lock):
        if "unix_socket_path" in self.kwargs:
            self.connection = yield makeUnixConnection(
                path=self.kwargs["unix_socket_path"],
                dbid=int(self.kwargs["db"]),
                poolsize=1,
                isLazy=False,
                reconnect=True,
                charset="UTF-8",
                password=self.kwargs.get("password") or None,
                connectTimeout=REDIS_CONNECTION_TIMEOUT,
                replyTimeout=REDIS_CONNECTION_TIMEOUT,
                convertNumbers=True,
                protocol=None,
            )
            makeUnixConnection(
                path=self.kwargs["unix_socket_path"],
                dbid=int(self.kwargs["db"]),
                poolsize=1,
                isLazy=True,
                reconnect=True,
                charset="UTF-8",
                password=self.kwargs.get("password"),
                connectTimeout=REDIS_CONNECTION_TIMEOUT,
                replyTimeout=REDIS_CONNECTION_TIMEOUT,
                convertNumbers=True,
                protocol=makeRedisPubSubProtocol(self),
            )
        else:
            self.connection = yield makeConnection(
                host=self.kwargs["host"],
                port=self.kwargs["port"],
                dbid=int(self.kwargs["db"]),
                poolsize=1,
                isLazy=False,
                reconnect=True,
                charset="UTF-8",
                password=self.kwargs.get("password") or None,
                connectTimeout=REDIS_CONNECTION_TIMEOUT,
                replyTimeout=REDIS_CONNECTION_TIMEOUT,
                convertNumbers=True,
                protocol=None,
            )
            makeConnection(
                host=self.kwargs["host"],
                port=self.kwargs["port"],
                dbid=int(self.kwargs["db"]),
                poolsize=1,
                isLazy=True,
                reconnect=True,
                charset="UTF-8",
                password=self.kwargs.get("password"),
                connectTimeout=REDIS_CONNECTION_TIMEOUT,
                replyTimeout=REDIS_CONNECTION_TIMEOUT,
                convertNumbers=True,
                protocol=makeRedisPubSubProtocol(self),
            )

        self._requeued_processing = False  # Requeue old processing on start

        if getattr(getConfiguration(), "debug_mode", False):
            # TODO: Should fail fast when Redis fails to connect
            pass

        yield self.mutex.release()

    @property
    @forever.memoize
    def redis_key(self):
        # XXX: On exception, something is firing before the queue has been registered
        return f"collective.taskqueue.{self.name:s}"

    @inlineCallbacks
    def __len__(self):
        try:
            queue_length = yield self.connection.llen(self.redis_key)
            return int(queue_length)
        except redis.ConnectionError:
            return 0

    def serialize(self, task):
        return msgpack.dumps(sorted(task.items()))

    def deserialize(self, msg):
        if msg is not None:
            return dict(msgpack.loads(msg))
        else:
            return None

    @inlineCallbacks
    def put(self, task):
        yield self.connection.lpush(self.redis_key, self.serialize(task))
        yield self.connection.publish(self.redis_key, "lpush")  # Send event

    @inlineCallbacks
    def get(self, consumer_name):
        yield self.mutex.acquire()

        consumer_key = f"{self.redis_key:s}.{consumer_name:s}"

        if not self._requeued_processing:
            yield self._requeue_processing(consumer_name)
        try:
            while True:
                task = yield self.connection.rpoplpush(self.redis_key, consumer_key)
                if task is not None:
                    break
                yield self.messages.get()  # Wait until new message event
        except redis.ConnectionError:
            task = None

        yield self.mutex.release()
        return self.deserialize(task)

    @inlineCallbacks
    def task_done(self, task, status_line, consumer_name, consumer_length):
        consumer_key = f"{self.redis_key:s}.{consumer_name:s}"

        consumed = yield self.connection.lrem(consumer_key, -1, self.serialize(task))
        assert consumed == 1, "Removal of consumed message failed"

        queue_length = yield self.connection.llen(consumer_key)
        if consumer_length == 0 and int(queue_length):
            yield self._requeue_processing(consumer_name)

    @inlineCallbacks
    def _requeue_processing(self, consumer_name):
        consumer_key = f"{self.redis_key:s}.{consumer_name:s}"

        try:
            while (yield self.connection.llen(consumer_key)) > 0:
                yield self.connection.rpoplpush(consumer_key, self.redis_key)
            yield self.connection.publish(self.redis_key, "rpoplpush")  # Send event
            self._requeued_processing = True
        except redis.ConnectionError:
            pass

    @inlineCallbacks
    def reset(self):
        for key in (yield self.connection.keys(self.redis_key + "*")):
            yield self.connection.ltrim(key, 1, 0)
