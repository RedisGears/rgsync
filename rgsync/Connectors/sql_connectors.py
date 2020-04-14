from rgsync.common import *
from redisgears import getMyHashTag as hashtag

class BaseSqlConnection():
    def __init__(self, user, passwd, db):
        self.user = user
        self.passwd = passwd
        self.db = db

    def _getConnectionStr(self):
        raise Exception('Can not use BaseSqlConnector _getConnectionStr directly')

    def Connect(self):
        from sqlalchemy import create_engine
        ConnectionStr = self._getConnectionStr()

        WriteBehindLog('Connect: connecting ConnectionStr=%s' % (ConnectionStr))
        engine = create_engine(ConnectionStr).execution_options(autocommit=True)
        conn = engine.connect()
        WriteBehindLog('Connect: Connected')
        return conn

class MySqlConnection(BaseSqlConnection):
    def __init__(self, user, passwd, db):
        BaseSqlConnection.__init__(self, user, passwd, db)

    def _getConnectionStr(self):
        return 'mysql+pymysql://{user}:{password}@{db}'.format(user=self.user, password=self.passwd, db=self.db)

class OracleSqlConnection(BaseSqlConnection):
    def __init__(self, user, passwd, db):
        BaseSqlConnection.__init__(self, user, passwd, db)

    def _getConnectionStr(self):
        return 'oracle://{user}:{password}@{db}'.format(user=self.user, password=self.passwd, db=self.db)

class SnowflakeSqlConnection(BaseSqlConnection):
    def __init__(self, user, passwd, db, account):
        BaseSqlConnection.__init__(self, user, passwd, db)
        self.account = account

    def _getConnectionStr(self):
        return 'snowflake://{user}:{password}@{account}/{db}'.format(user=self.user,
                                                                     password=self.passwd,
                                                                     account=self.account,
                                                                     db=self.db)


class BaseSqlConnector():
    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        self.connection = connection
        self.tableName = tableName
        self.pk = pk
        self.exactlyOnceTableName = exactlyOnceTableName
        self.exactlyOnceLastId = None
        self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
        self.conn = None
        self.supportedOperations = [OPERATION_DEL_REPLICATE, OPERATION_UPDATE_REPLICATE]

    def PrepereQueries(self, mappings):
        raise Exception('Can not use BaseSqlConnector PrepereQueries directly')

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
            if not self.conn:
                from sqlalchemy.sql import text
                self.sqlText = text
                self.conn = self.connection.Connect()
                if self.exactlyOnceTableName is not None:
                    shardId = 'shard-%s' % hashtag()
                    result = self.conn.execute(self.sqlText('select val from %s where id=:id' % self.exactlyOnceTableName, {'id':shardId}))
                    res = result.first()
                    if res is not None:
                        self.exactlyOnceLastId = str(res['val'])
                    else:
                        self.shouldCompareId = False
        except Exception as e:
            self.conn = None # next time we will reconnect to the database
            self.exactlyOnceLastId = None
            self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
            msg = 'Failed connecting to SQL database, error="%s"' % str(e)
            WriteBehindLog(msg)
            raise Exception(msg) from None

        idsToAck = []

        trans = self.conn.begin()
        try:
            batch = []
            # we have only key name, original_key, streamId, it means that the key was deleted
            isAddBatch = True if data[0][OP_KEY] == OPERATION_UPDATE_REPLICATE else False
            query = self.addQuery if isAddBatch else self.delQuery
            lastStreamId = None
            for x in data:
                lastStreamId = x.pop('streamId', None)## pop the stream id out of the record, we do not need it.
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
                        self.conn.execute(self.sqlText(query), batch)
                        batch = []
                        isAddBatch = False
                        query = self.delQuery
                    batch.append(x)
                else:
                    if not isAddBatch:
                        self.conn.execute(self.sqlText(query), batch)
                        batch = []
                        isAddBatch = True
                        query = self.addQuery
                    batch.append(x)
            if len(batch) > 0:
                self.conn.execute(self.sqlText(query), batch)
                if self.exactlyOnceTableName is not None:
                    self.conn.execute(self.sqlText(self.exactlyOnceQuery), {'id':shardId, 'val':lastStreamId})
            trans.commit()
        except Exception as e:
            try:
                trans.rollback()
            except Exception as e:
                WriteBehindLog('Failed rollback transaction')
            self.conn = None # next time we will reconnect to the database
            self.exactlyOnceLastId = None
            self.shouldCompareId = True if self.exactlyOnceTableName is not None else False
            msg = 'Got exception when writing to DB, query="%s", error="%s".' % ((query if query else 'None'), str(e))
            WriteBehindLog(msg)
            raise Exception(msg) from None

class MySqlConnector(BaseSqlConnector):
    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        BaseSqlConnector.__init__(self, connection, tableName, pk, exactlyOnceTableName)

    def PrepereQueries(self, mappings):
        def GetUpdateQuery(tableName, mappings, pk):
            query = 'REPLACE INTO %s' % tableName
            values = [val for kk, val in mappings.items() if not kk.startswith('_')]
            values = [self.pk] + values
            values.sort()
            query = '%s(%s) values(%s)' % (query, ','.join(values), ','.join([':%s' % a for a in values]))
            return query
        self.addQuery = GetUpdateQuery(self.tableName, mappings, self.pk)
        self.delQuery = 'delete from %s where %s=:%s' % (self.tableName, self.pk, self.pk)
        if self.exactlyOnceTableName is not None:
            self.exactlyOnceQuery = GetUpdateQuery(self.exactlyOnceTableName, {'val', 'val'}, 'id')

class OracleSqlConnector(BaseSqlConnector):
    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        BaseSqlConnector.__init__(self, connection, tableName, pk, exactlyOnceTableName)

    def PrepereQueries(self, mappings):
        values = [val for kk, val in mappings.items() if not kk.startswith('_')]
        values_with_pkey = [self.pk] + values
        def GetUpdateQuery(table, pkey, values_with_pkey, values):
            merge_into = "MERGE INTO %s d USING (SELECT 1 FROM DUAL) ON (d.%s = :%s)" % (table, pkey, pkey)
            not_matched = "WHEN NOT MATCHED THEN INSERT (%s) VALUES (%s)" % (','.join(values_with_pkey), ','.join([':%s' % a for a in values_with_pkey]))
            matched = "WHEN MATCHED THEN UPDATE SET %s" % (','.join(['%s=:%s' % (a,a) for a in values]))
            query = "%s %s %s" % (merge_into, not_matched, matched)
            return query
        self.addQuery = GetUpdateQuery(self.tableName, self.pk, values_with_pkey, values)
        self.delQuery = 'delete from %s where %s=:%s' % (self.tableName, self.pk, self.pk)
        if self.exactlyOnceTableName is not None:
            self.exactlyOnceQuery = GetUpdateQuery(self.exactlyOnceTableName, 'id', ['id', 'val'], ['val'])

class SnowflakeSqlConnector(OracleSqlConnector):
    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        OracleSqlConnector.__init__(self, connection, tableName, pk, exactlyOnceTableName)
