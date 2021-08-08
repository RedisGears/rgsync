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
        return self._user

    @property
    def password(self):
        return self._password

    @property
    def db(self):
        return self._db

    @property
    def collection(self):
        return self._collection