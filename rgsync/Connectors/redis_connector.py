from rgsync.common import *
from redisgears import getMyHashTag as hashtag


# redis connection class
class RedisConnection():
    def __init__(self, host, port, password=None):
        self._host = host
        self._port = port
        self._password = password

    @property
    def host(self):
        return self._host() if callable(self._host) else self._host

    @property
    def port(self):
        return self._port() if callable(self._port) else self._port

    @property
    def password(self):
        return self._password() if callable(self._password) else self._password

    def Connect(self):
        from redis.client import Redis
        try:
            WriteBehindLog("Connect: connecting to {}:{}".format(self.host, self.port))
            r = Redis(host=self.host, port=self.port, password=self.password, decode_responses=True)
        except Exception as e:
            msg = "Cannot connect to Redis. Exception: {}".format(e)
            WriteBehindLog(msg)
            raise Exception(msg) from None
        return r


# redis cluster connection class
class RedisClusterConnection():
    def __init__(self, host=None, port=None, cluster_nodes=None, password=None):
        self._host = host
        self._port = port
        self._cluster_nodes = cluster_nodes
        self._password = password

    @property
    def host(self):
        return self._host() if callable(self._host) else self._host

    @property
    def port(self):
        return self._port() if callable(self._port) else self._port

    @property
    def password(self):
        return self._password() if callable(self._password) else self._password

    @property
    def cluster_nodes(self):
        return self._cluster_nodes() if callable(self._cluster_nodes) else self._cluster_nodes

    def Connect(self):
        from rediscluster.client import RedisCluster
        try:
            WriteBehindLog("Connect: connecting to {}:{} cluster nodes: {}".format(self.host, self.port, self.cluster_nodes))
            rc = RedisCluster(host=self.host, port=self.port, startup_nodes=self.cluster_nodes, password=self.password, decode_responses=True)
        except Exception as e:
            msg = "Cannot connect to Redis Cluster. Exception: {}".format(e)
            WriteBehindLog(msg)
            raise Exception(msg) from None
        return rc


SIMPLE_HASH_BACKEND_PK = 'HashBackendPK'
SIMPLE_HASH_BACKEND_TABLE = 'HashBackendTable'

# redis connector class
class RedisConnector():
    def __init__(self, connection, newPrefix, exactlyOnceTableName=None):
        self.connection = connection
        self.session = None
        self.new_prefix = newPrefix
        self.supportedOperations = [OPERATION_DEL_REPLICATE, OPERATION_UPDATE_REPLICATE]
        self.exactlyOnceTableName = exactlyOnceTableName
        self.exactlyOnceLastId = None
        self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
        # Raise eception in case of exactly once property is used in RedisCluster
        if((self.exactlyOnceTableName is not None) and
                isinstance(self.connection, RedisClusterConnection)):
            msg = "Exactly once property is not valid for Redis cluster"
            raise Exception(msg) from None

    def TableName(self):
        return SIMPLE_HASH_BACKEND_TABLE

    def PrimaryKey(self):
        return SIMPLE_HASH_BACKEND_PK

    def WriteData(self, data):
        # return if no data is received to write
        if(0 == len(data)):
            WriteBehindLog("Warning: in connector received empty batch to write")
            return

        if not self.session:
            self.session = self.connection.Connect()

        # in case of exactly once get last id written
        shardId = None
        try:
            # Get the entry corresponding to shard id in exactly once table
            if((self.exactlyOnceTableName is not None) and
                    isinstance(self.connection, RedisConnection)):
                shardId = 'shard-%s' % hashtag()
                res = self.session.execute_command('HGET', self.exactlyOnceTableName, shardId)
                if res is not None:
                    self.exactlyOnceLastId = str(res)
                else:
                    self.shouldCompareId = False

        except Exception as e:
            self.session = None             #Next time we will connect to database
            self.exactlyOnceLastId = None
            self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
            msg = "Exception occur while getting shard id for exactly once. Exception : {}".format(e)
            WriteBehindLog(msg)
            raise Exception(msg) from None

        pipe = self.session.pipeline()
        try:
            # data is list of dictionaries
            # iterate over one by one and extract a dictionary and process it
            lastStreamId = None
            for d in data:
                d_val = d['value']              # get value of key 'value' from dictionary

                lastStreamId = d.pop('id', None)    # pop the stream id out of the record
                if self.shouldCompareId and CompareIds(self.exactlyOnceLastId, lastStreamId) >= 0:
                    WriteBehindLog('Skip {} as it was already written to the backend'.format(lastStreamId))
                    continue

                self.shouldCompareId = False

                # check operation permission, what gets replicated
                op = d_val.pop(OP_KEY, None)        # pop the operation key out of the record
                if op not in self.supportedOperations:
                    msg = 'Got unknown operation'
                    raise Exception(msg) from None

                pk = d_val.pop(SIMPLE_HASH_BACKEND_PK)
                newKey = '{}:{}'.format(self.new_prefix, pk)

                if op != OPERATION_UPDATE_REPLICATE:
                    # pipeline key to delete
                    pipe.delete(newKey)
                else:
                    # pipeline key and field-value mapping to set
                    pipe.hset(newKey, mapping=d_val)

                # make entry for exactly once. In case of Redis cluster exception will be raised already
                if((self.exactlyOnceTableName is not None) and
                        isinstance(self.connection, RedisConnection)):
                    l_exact_once_val = {shardId : lastStreamId}
                    pipe.hset(self.exactlyOnceTableName, mapping=l_exact_once_val)

            #execute pipeline ommands
            pipe.execute()

        except Exception as e:
            self.session.close()
            self.session = None             # next time we will reconnect to the database
            self.exactlyOnceLastId = None
            self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
            msg = "Got exception when writing to DB, Exception : {}".format(e)
            WriteBehindLog(msg)
            raise Exception(msg) from None

####################
#       EOF
####################
