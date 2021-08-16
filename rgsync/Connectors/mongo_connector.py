from rgsync.common import *

class MongoConnection(object):

    def __init__(self, user, password, db):
        self._user = user
        self._password = password
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

    @property
    def _getConnectionStr(self):
        con = "mongodb://{}:{}@{}?authSource=admin&authMechanism=SCRAM-SHA-256".format(
            self.user,
            self.password,
            self.db,
        )
        return con

    def Connect(self):
        from pymongo import MongoClient
        WriteBehindLog('Connect: connecting')
        client = MongoClient(self._getConnectionStr)
        client.server_info()  # there is no other way to test a connection
        WriteBehindLog('Connect: Connected')
        return client[self.db]


class MongoConnector:

    def __init__(self, connection, tableName, pk, exactlyOnceTableName=None):
        self.conection = connection
        self.tableName = tableName
        self.pk = pk
        self.exactlyOnceTableName = exactlyOnceTableName
        self.supportedOperations = [OPERATION_DEL_REPLICATE, OPERATION_UPDATE_REPLICATE]

    def TableName(self):
        return self.tableName

    def PrimaryKey(self):
        return self.pk

    def PrepereQueries(self, mappings):

        def GetUpdateQuery(tableName, mappings, pk):
            newmap = {k: v for k,v in mappings.items() if not k.find('_') == 0}
            query = {"$set": newmap}
            return query

        self.delQuery = self.TableName().delete_one({'id': self.PrimaryKey()})
        self.addQuery = GetUpdateQuery(self.tableName, mappings, self.pk)