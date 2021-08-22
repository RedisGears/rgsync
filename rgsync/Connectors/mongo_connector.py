from rgsync.common import *
from pymongo import InsertOne, ReplaceOne, DeleteOne

class MongoConnection(object):

    def __init__(self, user, password, db, authSource="admin"):
        self._user = user
        self._passwd = password
        self._db = db

        # mongo allows one to authenticate against different databases
        self._authSource = authSource

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
        self.connection = connection.Connect()
        self.collection = self.connection[db][tableName]
        self.pk = pk
        self.exactlyOnceTableName = exactlyOnceTableName
        self.exactlyOnceLastId = None
        self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
        self.supportedOperations = [OPERATION_DEL_REPLICATE, OPERATION_UPDATE_REPLICATE]

    # def TableName(self):
    #     return self.tableName

    def PrimaryKey(self):
        return self.pk

    def PrepereQueries(self, mappings):

        def GetUpdateQuery(mappings, pk):
            query = {k: v for k,v in mappings.items() if not k.find('_') == 0}
            query['_id'] = pk
            return ReplaceOne(filter={'_id': pk}, replacement=query, upsert=True)

        self.delQuery = DeleteOne({'_id': self.PrimaryKey()})
        self.addQuery = InsertOne(GetUpdateQuery(mappings, self.pk))
        self.exactlyOnceQuery = GetUpdateQuery({'val', 'val'}, '_id')

    def WriteData(self, data):
        if len(data) == 0:
            WriteBehindLog('Warning, got an empty batch')
            return

        query = None
        isAddBatch = True if data[0]['value'][OP_KEY] == OPERATION_UPDATE_REPLICATE else False
        query = self.addQuery if isAddBatch else self.delQuery
        lastStreamId = None

        try:
            if not self.conn:
                from sqlalchemy.sql import text
                self.sqlText = text
                con = self.connection.Connect()
                if self.exactlyOnceTableName is not None:
                    collection = con[self.db][self.exactlyOnceTableName]
                    shardId = 'shard-%s' % hashtag()
                    result = collection.find_one({"_id", shardId})
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

        idsToAck = []

        try:
            with self.connection.Connect().start_session() as session:
                with session.start_transaction():
                    for d in data:
                        x = d['value']

                        lastStreamId = d.pop('id', None)## pop the stream id out of the record, we do not need it.
                        if self.shouldCompareId and CompareIds(self.exactlyOnceLastId, lastStreamId) >= 0:
                            WriteBehindLog('Skip %s as it was already writen to the backend' % lastStreamId)
                            continue

                        op = x.pop(OP_KEY, None)
                        if op not in self.supportedOperations:
                            msg = 'Got unknown operation'
                            WriteBehindLog(msg)
                            raise Exception(msg) from None

                        self.shouldCompareId = False
                        if op != OPERATION_UPDATE_REPLICATE: # we have only key name, it means that the key was deleted
                            if isAddBatch:
                                self.collection.bulk_write(batch)
                                batch = []
                                isAddBatch = False
                                query = self.delQuery
                            batch.append(x)
                        else:
                            if not isAddBatch:
                                self.collection.bulk_write(batch)
                                batch = []
                                isAddBatch = True
                                query = self.addQuery
                            batch.append(x)

                    if len(batch) > 0:
                            self.collection.bulk_write(batch)

        except Exception as e:
            self.exactlyOnceLastId = None
            self.shouldCompareId = False
            msg = 'Got exception when writing to DB, query="%s", error="%s".' % ((query if query else 'None'), str(e))
            WriteBehindLog(msg)
            raise Exception(msg) from None