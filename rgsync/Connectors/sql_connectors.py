from rgsync.common import *
from redisgears import getMyHashTag as hashtag
from collections import OrderedDict

class BaseSqlConnection():
    def __init__(self, user, passwd, db):
        self._user = user
        self._passwd = passwd
        self._db = db

    @property
    def user(self):
        return self._user() if callable(self._user) else self._user

    @property
    def passwd(self):
        return self._passwd() if callable(self._passwd) else self._passwd

    @property
    def db(self):
        return self._db() if callable(self._db) else self._db

    def _getConnectionStr(self):
        raise Exception('Can not use BaseSqlConnector _getConnectionStr directly')

    def Connect(self):
        from sqlalchemy import create_engine
        ConnectionStr = self._getConnectionStr()

        WriteBehindLog('Connect: connecting')
        engine = create_engine(ConnectionStr).execution_options(autocommit=True)
        conn = engine.connect()
        WriteBehindLog('Connect: Connected')
        return conn

class MySqlConnection(BaseSqlConnection):
    def __init__(self, user, passwd, db):
        BaseSqlConnection.__init__(self, user, passwd, db)

    def _getConnectionStr(self):
        return 'mysql+pymysql://{user}:{password}@{db}'.format(user=self.user, password=self.passwd, db=self.db)

class PostgresConnection(BaseSqlConnection):
    def __init__(self, user, passwd, db):
        BaseSqlConnection.__init__(self, user, passwd, db)

    def _getConnectionStr(self):
        return 'postgresql://{user}:{password}@{db}'.format(user=self.user, password=self.passwd, db=self.db)

class SQLiteConnection(BaseSqlConnection):
    def __init__(self, filePath):
        BaseSqlConnection.__init__(self, None, None, None)
        self._filePath = filePath

    @property
    def filePath(self):
        return self._filePath() if callable(self._filePath) else self._filePath

    def _getConnectionStr(self):
        return 'sqlite:////{filePath}?check_same_thread=False'.format(filePath=self.filePath)

class OracleSqlConnection(BaseSqlConnection):
    def __init__(self, user, passwd, db):
        BaseSqlConnection.__init__(self, user, passwd, db)

    def _getConnectionStr(self):
        return 'oracle://{user}:{password}@{db}'.format(user=self.user, password=self.passwd, db=self.db)

class MsSqlConnection(BaseSqlConnection):
    def __init__(self, user, passwd, db, server, port, driver):
        BaseSqlConnection.__init__(self, user, passwd, db)
        self._server=server
        self._port=port
        self._driver=driver
    @property
    def server(self):
        return self._server() if callable(self._server) else self._server
    @property
    def port(self):
        return self._port() if callable(self._port) else self._port
    @property
    def driver(self):
        return self._driver() if callable(self._driver) else self._driver
    def _getConnectionStr(self):
        return 'mssql+pyodbc://{user}:{password}@{server}:{port}/{db}?driver={driver}'.format(user=self.user, password=self.passwd, db=self.db, server=self.server, port=self.port, driver=self.driver)

class SnowflakeSqlConnection(BaseSqlConnection):
    def __init__(self, user, passwd, db, account):
        BaseSqlConnection.__init__(self, user, passwd, db)
        self._account = account

    @property
    def account(self):
        return self._account() if callable(self._account) else self._account

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
                    result = self.conn.execute(self.sqlText('select val from %s where id=:id' % self.exactlyOnceTableName), {'id':shardId})
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
            isAddBatch = True if data[0]['value'][OP_KEY] == OPERATION_UPDATE_REPLICATE else False
            query = self.addQuery if isAddBatch else self.delQuery
            lastStreamId = None
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
            query = 'INSERT INTO %s' % tableName
            values = [val for kk, val in mappings.items() if not kk.startswith('_')]
            values = [pk] + values
            values.sort()
            query = '%s (%s) VALUES (%s) ON DUPLICATE KEY UPDATE %s' % (query, ','.join(values), ','.join([':%s' % a for a in values]), ','.join(['%s=values(%s)' % (a,a) for a in values]))

            return query
        self.addQuery = GetUpdateQuery(self.tableName, mappings, self.pk)
        self.delQuery = 'delete from %s where %s=:%s' % (self.tableName, self.pk, self.pk)
        if self.exactlyOnceTableName is not None:
            self.exactlyOnceQuery = GetUpdateQuery(self.exactlyOnceTableName, {'val', 'val'}, 'id')


class PostgresConnector(BaseSqlConnector):

    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        BaseSqlConnector.__init__(self, connection, tableName, pk, exactlyOnceTableName)

    def PrepereQueries(self, mappings):
        def GetUpdateQuery(tableName, mappings, pk):

            # OrderedDicts mean the same results each time
            ordered_mappings = OrderedDict(mappings)
            cols = ','.join(ordered_mappings.values())
            values = [":{}".format(val) for kk, val in ordered_mappings.items() if not kk.startswith('_')]
            values = list(values) + [":" + self.pk]

            # prepare statement
            value_stmt = ','.join(v for v in values)
            update_stmts = ["{}=excluded.{}".format(v, v) for v in ordered_mappings.values() if not v.startswith('_')]
            query = """INSERT INTO {} ({},{})
            VALUES ({})
            ON CONFLICT({}) DO UPDATE
            SET
            {}""".format(tableName, cols, pk,
                    value_stmt,
                    pk,
                    ', '.join(update_stmts))
            return query
        self.addQuery = GetUpdateQuery(self.tableName, mappings, self.pk)
        self.delQuery = 'delete from %s where %s=:%s' % (self.tableName, self.pk, self.pk)
        if self.exactlyOnceTableName is not None:
            self.exactlyOnceQuery = GetUpdateQuery(self.exactlyOnceTableName, {'val', 'val'}, 'id')


class SQLiteConnector(BaseSqlConnector):
    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        BaseSqlConnector.__init__(self, connection, tableName, pk, exactlyOnceTableName)

    def PrepereQueries(self, mappings):
        def GetUpdateQuery(tableName, mappings, pk):
            query = 'INSERT OR REPLACE INTO %s' % tableName
            values = [val for kk, val in mappings.items() if not kk.startswith('_')]
            values = [pk] + values
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

class MsSqlConnector(BaseSqlConnector):
    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        BaseSqlConnector.__init__(self, connection, tableName, pk, exactlyOnceTableName)
    def PrepereQueries(self, mappings):
        values = [val for kk, val in mappings.items() if not kk.startswith('_')]
        values_with_pkey = [self.pk] + values
        def GetUpdateQuery(tableName, mappings, pk):
            merge_into = "MERGE %s AS Target USING (VALUES (:%s)) AS Source (key1) ON (Target.%s = Source.key1)" % (tableName, pk, pk)
            not_matched = "WHEN NOT MATCHED BY TARGET THEN INSERT (%s) VALUES (%s)" % (','.join(values_with_pkey), ','.join([':%s' % a for a in values_with_pkey]))
            matched = "WHEN MATCHED THEN UPDATE SET %s" % (','.join(['Target.%s=:%s' % (a,a) for a in values]))
            query = "%s %s %s;" % (merge_into, not_matched, matched)
            return query
        self.addQuery = GetUpdateQuery(self.tableName, mappings, self.pk)
        self.delQuery = 'delete from %s where %s=:%s' % (self.tableName, self.pk, self.pk)
        if self.exactlyOnceTableName is not None:
            self.exactlyOnceQuery = GetUpdateQuery(self.exactlyOnceTableName, {'val', 'val'}, 'id')

class SnowflakeSqlConnector(OracleSqlConnector):
    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        OracleSqlConnector.__init__(self, connection, tableName, pk, exactlyOnceTableName)
