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
        WriteBehindLog("Connect: connecting to %s:%d password: %s" % (self.host, self.port, self.password))
        try:
            r = Redis(host=self.host, port=self.port, password=self.password)
        except Exception as e:
            WriteBehindLog("Cannot connect to Redis. Aborting (%s)" % str(e))
        WriteBehindLog("Connect: connected")
        return r

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

    def TableName(self):
        return SIMPLE_HASH_BACKEND_TABLE

    def PrimaryKey(self):
        return SIMPLE_HASH_BACKEND_PK

    def WriteData(self, data):
        # return if no data is received to write
        if(0 == len(data)):
            WriteBehindLog("Warning: in connector received empty batch to write")
            return

        try:
            if not self.session:
                self.session = self.connection.Connect()
                if self.exactlyOnceTableName is not None:
                    shardId = 'shard-%s' % hashtag()
                    res = self.session.execute_command('HGET', self.exactlyOnceTableName, shardId)
                    if 'ERR' in str(res):
                        WriteBehindLog("Error: Failed to get entry for exactly once key: %s, field: %s" 
                                % (self.exactlyOnceTableName, shardId))
                        WriteBehindLog("Error: Command HGET execution failed, error = %s" % str(res))
                        raise Exception(res) from None
                    elif res is not None:
                        self.exactlyOnceLastId = str(res)
                    else:
                        self.shouldCompareId = False

        except Exception as e:
            self.session = None     #Next time we will connect to database
            self.exactlyOnceLastId = None
            self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
            msg = "Failed to connect to Redis database, error = %s" % str(e)
            WriteBehindLog(msg)
            raise Exception(msg) from None


        try:

            # data is list of dictionaries
            # iterate over one by one and extract a dictionary and process it
            for d in data:
                d_val = d['value']              # get value of key 'value' from dictionary

                lastStreamId = d.pop('id', None)    # pop the stream id out of the record, we do not need it
                if self.shouldCompareId and CompareIds(self.exactlyOnceLastId, lastStreamId) >= 0:
                    WriteBehindLog('Skip %s as it was already writen to the backend' % lastStreamId)
                    continue

                # check operation permission, what gets replicated
                op = d_val.pop(OP_KEY, None)
                if op not in self.supportedOperations:
                    msg = 'Got unknown operation'
                    WriteBehindLog(msg)
                    raise Exception(msg) from None

                self.shouldCompareId = False
                pk = d_val.pop(SIMPLE_HASH_BACKEND_PK)
                newKey = '%s:%s' % (self.new_prefix, pk)

                if op == OPERATION_UPDATE_REPLICATE:
                    d = [[k, v] for k,v in d_val.items() if not k.startswith('_')]
                    res = self.session.execute_command('HSET', newKey, *sum(d, []))
                    if 'ERR' in str(res):
                        WriteBehindLog("Error: Command HSET execution failed, error = %s" % str(res))
                        raise Exception(res) from None 
                else:
                    res = self.session.execute_command('DEL', newKey)
                    if 'ERR' in str(res):
                        WriteBehindLog("Error: Command DEL execution failed, error = %s" % str(res))
                        raise Exception(res) from None
                    
                # make entry for exactly once
                if self.exactlyOnceTableName is not None:
                    res = self.session.execute_command('HSET', self.exactlyOnceTableName, shardId, lastStreamId)
                    if 'ERR' in str(res):
                        WriteBehindLog("Error: Entry for exactly once failed key: %s, field: %s, value: %s" 
                                % (self.exactlyOnceTableName, shardId, lastStreamId))
                        WriteBehindLog("Error: Command HSET execution failed, error = %s" % str(res))
                        raise Exception(res) from None

        except Exception as e:
            self.session.close()
            self.session = None     # # next time we will reconnect to the database
            self.exactlyOnceLastId = None
            self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
            msg = "Got exception when writing to DB, error = %s" % str(e)
            WriteBehindLog(msg)
            raise Exception(msg) from None

####################
#       EOF
####################
