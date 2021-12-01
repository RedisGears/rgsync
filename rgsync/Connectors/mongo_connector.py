from rgsync.common import *
import json
from pymongo import UpdateOne, ReplaceOne, DeleteOne

class MongoConnection(object):

    def __init__(self, user, password, db, authSource="admin", conn_string=None):
        self._user = user
        self._passwd = password
        self._db = db

        # mongo allows one to authenticate against different databases
        self._authSource = authSource
        self._conn_string = conn_string

    @property
    def user(self):
        return self._user() if callable(self._user) else self._user

    @property
    def passwd(self):
        return self._passwd() if callable(self._passwd) else self._passwd

    @property
    def db(self):
        return self._db() if callable(self._db) else self._db
    
    @property
    def _getConnectionStr(self):
        if self._conn_string is not None:
            return self._conn_string
        
        con = "mongodb://{}:{}@{}?authSource={}".format(
            self.user,
            self.passwd,
            self.db,
            self._authSource
        )
        return con

    def Connect(self):
        from pymongo import MongoClient
        WriteBehindLog('Connect: connecting')
        client = MongoClient(self._getConnectionStr)
        client.server_info()  # light connection test
        WriteBehindLog('Connect: Connected')
        return client

class MongoConnector:


    def __init__(self, connection, db, tableName, pk, exactlyOnceTableName=None):
        self.connection = connection
        self.tableName = tableName
        self.db = db
        self.pk = pk
        self.exactlyOnceTableName = exactlyOnceTableName
        self.exactlyOnceLastId = None
        self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
        self.supportedOperations = [OPERATION_DEL_REPLICATE, OPERATION_UPDATE_REPLICATE]

    @property    
    def collection(self):
        return self.connection.Connect()[self.db][self.tableName]

    def TableName(self):
        return self.tableName

    def PrimaryKey(self):
        return self.pk

    def DeleteQuery(self, mappings):
        rr = DeleteOne({self.PrimaryKey(): mappings[self.PrimaryKey()]})
        return rr

    def AddOrUpdateQuery(self, mappings, dataKey):
        import json
        query = {k: v for k,v in mappings.items() if not k.find('_') == 0}
        # try to decode the nest - only one level deep given the mappings

        update = {}
        for k, v in query.items():
            try:
                query[k] = json.loads(v.replace("'", '"'))
            except Exception as e:
                query[k] = v

            # flatten the key, to support partial updates
            if k == dataKey:
                update = {i: val for i, val in query.pop(k).items()}
                break

        query.update(update)

        rr = UpdateOne(filter={self.PrimaryKey(): mappings[self.PrimaryKey()]}, 
                       update={"$set": query}, upsert=True)
        return rr

    def WriteData(self, data, dataKey):
        if len(data) == 0:
            WriteBehindLog('Warning, got an empty batch')
            return

        query = None
        lastStreamId = None

        try:
            if self.exactlyOnceTableName is not None:
                shardId = 'shard-%s' % hashtag()
                result = self.collection().find_one({"_id", shardId})
                if result is not None:
                    self.exactlyOnceLastId = result['_id']
                else:
                    self.shouldCompareId = False

        except Exception as e:
            self.exactlyOnceLastId = None
            self.shouldCompareId = False
            msg = 'Failed connecting to database, error="%s"' % str(e)
            WriteBehindLog(msg)
            raise Exception(msg) from None

        batch = []

        for d in data:
            x = d['value']

            lastStreamId = d.pop('id', None)## pop the stream id out of the record, we do not need it.
            if self.shouldCompareId and CompareIds(self.exactlyOnceLastId, lastStreamId) >= 0:
                WriteBehindLog('Skip %s as it was already writen to the backend' % lastStreamId)

            op = x.pop(OP_KEY, None)
            if op not in self.supportedOperations:
                msg = 'Got unknown operation'
                WriteBehindLog(msg)
                raise Exception(msg) from None

            self.shouldCompareId = False
            if op == OPERATION_DEL_REPLICATE:
                batch.append(self.DeleteQuery(x))
            elif op == OPERATION_UPDATE_REPLICATE:
                batch.append(self.AddOrUpdateQuery(x, dataKey))

        try:
            if len(batch) > 0:
                r = self.collection.bulk_write(batch)

        except Exception as e:
            self.exactlyOnceLastId = None
            self.shouldCompareId = False
            msg = 'Got exception when writing to DB, query="%s", error="%s".' % ((query if query else 'None'), str(e))
            WriteBehindLog(msg)
            raise Exception(msg) from None