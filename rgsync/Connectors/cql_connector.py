from rgsync.common import *
from redisgears import getMyHashTag as hashtag
import json

class CqlConnection():
    def __init__(self, user, password, db, keyspace):
        self._user = user
        self._password = password
        self._db = db
        self._keyspace = keyspace

    @property
    def user(self):
        return self._user() if callable(self._user) else self._user

    @property
    def password(self):
        return self._password() if callable(self._password) else self._password

    @property
    def db(self):
        return self._db() if callable(self._db) else self._db

    @property
    def keyspace(self):
        return self._keyspace() if callable(self._keyspace) else self._keyspace

    def _getConnectionStr(self):
        return json.dumps({'user': self.user, 'password': self.password, 'db': self.db, 'keyspace': self.keyspace})

    def Connect(self):
        from cassandra.cluster import Cluster
        from cassandra.auth import PlainTextAuthProvider

        ConnectionStr = self._getConnectionStr()

        WriteBehindLog('Connect: connecting db=%s keyspace=%s' % (self.db, self.keyspace))
        auth_provider = PlainTextAuthProvider(username=self.user, password=self.password)
        cluster = Cluster(self.db.split(), auth_provider=auth_provider)
        if self.keyspace != '':
            session = cluster.connect(self.keyspace)
        else:
            session = cluster.connect()
        WriteBehindLog('Connect: Connected')
        return session


class CqlConnector:
    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        self.connection = connection
        self.tableName = tableName
        self.pk = pk
        self.exactlyOnceTableName = exactlyOnceTableName
        self.exactlyOnceLastId = None
        self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
        self.session = None
        self.supportedOperations = [OPERATION_DEL_REPLICATE, OPERATION_UPDATE_REPLICATE]

    def PrepereQueries(self, mappings):
        def GetUpdateQuery(tableName, mappings, pk):
            query = 'update %s set ' % tableName
            fields = ['%s=?' % (val) for kk, val in mappings.items() if not kk.startswith('_')]
            query += ','.join(fields)
            query += ' where %s=?' % (self.pk)
            return query
        self.addQuery = GetUpdateQuery(self.tableName, mappings, self.pk)
        self.delQuery = 'delete from %s where %s=?' % (self.tableName, self.pk)
        if self.exactlyOnceTableName is not None:
            self.exactlyOnceQuery = GetUpdateQuery(self.exactlyOnceTableName, {'val', 'val'}, 'id')

    def TableName(self):
        return self.tableName

    def PrimaryKey(self):
        return self.pk

    def WriteData(self, data):
        if len(data) == 0:
            WriteBehindLog('Warning, got an empty batch')
            return
        query = None

        try:
            if not self.session:
                self.session = self.connection.Connect()
                if self.exactlyOnceTableName is not None:
                    shardId = 'shard-%s' % hashtag()
                    result = self.session.execute('select val from %s where id=?' % self.exactlyOnceTableName, shardId)
                    res = result.first()
                    if res is not None:
                        self.exactlyOnceLastId = str(res['val'])
                    else:
                        self.shouldCompareId = False
        except Exception as e:
            self.session = None # next time we will reconnect to the database
            self.exactlyOnceLastId = None
            self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
            msg = 'Failed connecting to Cassandra database, error="%s"' % str(e)
            WriteBehindLog(msg)
            raise Exception(msg) from None

        idsToAck = []

        try:
            from cassandra.cluster import BatchStatement
            batch = BatchStatement()
            isAddBatch = True if data[0]['value'][OP_KEY] == OPERATION_UPDATE_REPLICATE else False
            query = self.addQuery if isAddBatch else self.delQuery
            stmt = self.session.prepare(query)
            lastStreamId = None
            for d in data:
                x = d['value']
                lastStreamId = d.pop('id', None) # pop the stream id out of the record, we do not need it
                if self.shouldCompareId and CompareIds(self.exactlyOnceLastId, lastStreamId) >= 0:
                    WriteBehindLog('Skip %s as it was already writen to the backend' % lastStreamId)
                    continue

                op = x.pop(OP_KEY, None)
                if op not in self.supportedOperations:
                    msg = 'Got unknown operation'
                    WriteBehindLog(msg)
                    raise Exception(msg) from None

                self.shouldCompareId = False
                if op != OPERATION_UPDATE_REPLICATE:
                    if isAddBatch:
                        self.session.execute(batch)
                        batch = BatchStatement()
                        isAddBatch = False
                        query = self.delQuery
                else:
                    if not isAddBatch:
                        self.session.execute(batch)
                        batch = BatchStatement()
                        isAddBatch = True
                        query = self.addQuery
                stmt = self.session.prepare(query)
                batch.add(stmt.bind(x))
            if len(batch) > 0:
                self.session.execute(batch)
                if self.exactlyOnceTableName is not None:
                    stmt = self.session.prepare(self.exactlyOnceQuery)
                    self.session.execute(stmt, {'id':shardId, 'val':lastStreamId})
        except Exception as e:
            self.session = None # next time we will reconnect to the database
            self.exactlyOnceLastId = None
            self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
            msg = 'Got exception when writing to DB, query="%s", error="%s".' % ((query if query else 'None'), str(e))
            WriteBehindLog(msg)
            raise Exception(msg) from None
