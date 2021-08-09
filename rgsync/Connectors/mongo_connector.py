from rgsync.common import *
import json

class MongoConnection():

    def __init__(self, user, password, db, collection):
        self._user = user
        self._password = password
        self._db = db
        self._collection = collection

    @property
    def user(self):
        return self._user() if callable(self._user) else self._user

    @property
    def passwd(self):
        return self._passwd() if callable(self._passwd) else self._passwd

    @property
    def db(self):
        return self._db() if callable(self._db) else self._db

    # @property
    # def collection(self):
    #     return self._collection

    @property
    def _getConnectionStr(self):
        return "mongodb://{}:{}".format(self.user, self.passwd)

    def Connect(self):
        from pymongo import MongoClient
        WriteBehindLog('Connect: connecting ConnectionStr={}'.format(self._getConnectionStr))
        client = MongoClient(self._getConnectionStr, serverSelectionTimeoutMS=5000)
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