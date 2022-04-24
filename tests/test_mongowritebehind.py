import pytest
import string
import random
import json
import time
import tox
from redis import Redis
# from RLTest import Env
from pymongo import MongoClient
from tests import find_package


@pytest.mark.mongo
class TestMongoJSON:

    def teardown_method(self):
        self.dbconn.drop_database(self.DBNAME)
        self.env.flushall()

    @classmethod
    def setup_class(cls):
        cls.env = Redis(decode_responses=True)

        pkg = find_package()

        # connection info
        r = tox.config.parseconfig(open("tox.ini").read())
        docker = r._docker_container_configs["mongo"]["environment"]
        dbuser = docker["MONGO_INITDB_ROOT_USERNAME"]
        dbpasswd = docker["MONGO_INITDB_ROOT_PASSWORD"]
        db = docker["MONGO_DB"]

        con = "mongodb://{user}:{password}@172.17.0.1:27017/{db}?authSource=admin".format(
            user=dbuser,
            password=dbpasswd,
            db=db,
        )

        script = """
from rgsync import RGJSONWriteBehind, RGJSONWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

connection = MongoConnection('%s', '%s', '172.17.0.1:27017/%s')
db = '%s'

jConnector = MongoConnector(connection, db, 'persons', 'person_id')

RGJSONWriteBehind(GB,  keysPrefix='person',
              connector=jConnector, name='PersonsWriteBehind',
              version='99.99.99')

RGJSONWriteThrough(GB, keysPrefix='__', connector=jConnector,
                   name='JSONWriteThrough', version='99.99.99')
""" % (dbuser, dbpasswd, db, db)
        cls.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymongo')

        e = MongoClient(con)

        # # tables are only created upon data use - so this is our equivalent
        # # for mongo
        assert 'version' in e.server_info().keys()
        cls.dbconn = e
        cls.DBNAME = db

    def _sampledata(self):
        d = {'some': 'value',
             'and another': ['set', 'of', 'values']
        }
        return d

    def _base_writebehind_validation(self):
        self.env.execute_command('json.set', 'person:1', '.', json.dumps(self._sampledata()))
        result = list(self.dbconn[self.DBNAME]['persons'].find())
        count = 0
        while len(result) == 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())
            if count == 10:
                assert False == True, "Failed writing data to mongo"
                break
            count += 1

        assert 'gears'not in result[0].keys()
        assert 1 == int(result[0]['person_id'])
        assert 'value' == result[0]['some']
        assert ['set', 'of', 'values'] == result[0]['and another']

    def testSimpleWriteBehind(self):
        self._base_writebehind_validation()

        self.env.execute_command('json.del', 'person:1')
        result = list(self.dbconn[self.DBNAME]['persons'].find())
        count = 0
        while len(result) != 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())
            if count == 10:
                assert False == True, "Failed deleting data from mongo"
                break
            count += 1

    def testGiantWriteBehind(self):
        large_blob = {
            "firstName": "Just",
            "lastName": "Aperson",
            "age": 24,
            "address": {
                "streetAddress": "123 Fake Street",
                "city": "Springfield",
                "state": "IL",
                "postalCode": "123456"
            },
            "phoneNumbers": [
                { "type": "home", "number": "1234567890" }
            ],
            "GlossTerm": "Standard Generalized Markup Language",
            "Acronym": "SGML",
            "Abbrev": "ISO 8879:1986",
            "GlossDef": {
                "para": "A meta-markup language, used to create markup languages such as DocBook.",
                "GlossSeeAlso": ["GML", "XML"]
            },
            "GlossSee": "markup"
        }

        for i in range(1, 255):
            key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))
            val = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
            large_blob[key] = val

        self.env.execute_command('json.set', 'person:1', '.', json.dumps(large_blob))

        result = list(self.dbconn[self.DBNAME]['persons'].find())
        count = 0
        while len(result) == 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())
            if count == 10:
                assert False == True, "Failed writing data to mongo"
                break
            count += 1

        for key in large_blob:
            assert key in result[0].keys()
            assert result[0][key] == large_blob[key]

    def testStraightDelete(self):
        self._base_writebehind_validation()
        self.env.execute_command('del', 'person:1')

        result = list(self.dbconn[self.DBNAME]['persons'].find())
        count = 0
        while len(result) != 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())
            if count == 10:
                assert False == True, "Failed deleting data from mongo"
                break
            count += 1

    def testSimpleWriteThroughPartialUpdate(self):
        self._base_writebehind_validation()

        result = list(self.dbconn[self.DBNAME]['persons'].find())

        ud = {'some': 'not a value!'}
        self.env.execute_command('json.set', 'person:1', '.', json.dumps(ud))

        # need replication time
        result = list(self.dbconn[self.DBNAME]['persons'].find())
        count = 0
        while count != 10:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())
            if result[0]['some'] == 'not a value!':
                break
            else:
                count += 1

        if count == 10:
            assert False == True, "Failed to update sub value!"

        assert result[0]['person_id'] == '1'

    def testUpdatingWithFieldsNotInMap(self):
        self._base_writebehind_validation()

        result = list(self.dbconn[self.DBNAME]['persons'].find())

        ud = {'somerandomthing': 'this too is random!'}
        self.env.execute_command('json.set', 'person:1', '.', json.dumps(ud))

        # need replication time
        result = list(self.dbconn[self.DBNAME]['persons'].find())
        count = 0
        while count != 10:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())
            if 'somerandomthing' not in result[0].keys():
                count += 1
            else:
                assert result[0]['somerandomthing'] == 'this too is random!'
                break

        if count == 10:
            assert False == True, "Failed to update sub value!"

        assert result[0]['person_id'] == '1'


@pytest.mark.mongo
class TestMongoConnString(TestMongoJSON):
    """Mongo tests, using a connection string for the database side."""

    @classmethod
    def setup_class(cls):
        cls.env = Redis(decode_responses=True)

        pkg = find_package()

        # connection info
        r = tox.config.parseconfig(open("tox.ini").read())
        docker = r._docker_container_configs["mongo"]["environment"]
        dbuser = docker["MONGO_INITDB_ROOT_USERNAME"]
        dbpasswd = docker["MONGO_INITDB_ROOT_PASSWORD"]
        db = docker["MONGO_DB"]

        con = "mongodb://{user}:{password}@172.17.0.1:27017/{db}?authSource=admin".format(
            user=dbuser,
            password=dbpasswd,
            db=db,
        )

        script = """
from rgsync import RGJSONWriteBehind, RGJSONWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

db = '%s'
conn_string = '%s'
connection = MongoConnection(None, None, db, None, conn_string)

jConnector = MongoConnector(connection, db, 'persons', 'person_id')

RGJSONWriteBehind(GB,  keysPrefix='person',
              connector=jConnector, name='PersonsWriteBehind',
              version='99.99.99')

RGJSONWriteThrough(GB, keysPrefix='__', connector=jConnector,
                   name='JSONWriteThrough', version='99.99.99')
""" % (db, con)
        cls.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymongo')

        e = MongoClient(con)

        # # tables are only created upon data use - so this is our equivalent
        # # for mongo
        assert 'version' in e.server_info().keys()
        cls.dbconn = e
        cls.DBNAME = db


@pytest.mark.mongo
class TestMongoJSONDualKeys:

   def teardown_method(self):
        self.dbconn.drop_database(self.DBNAME)
        self.env.flushall()


   @classmethod
   def setup_class(cls):
        cls.env = Redis(decode_responses=True)

        pkg = find_package()

        # connection info
        r = tox.config.parseconfig(open("tox.ini").read())
        docker = r._docker_container_configs["mongo"]["environment"]
        dbuser = docker["MONGO_INITDB_ROOT_USERNAME"]
        dbpasswd = docker["MONGO_INITDB_ROOT_PASSWORD"]
        db = docker["MONGO_DB"]

        con = "mongodb://{user}:{password}@172.17.0.1:27017/{db}?authSource=admin".format(
            user=dbuser,
            password=dbpasswd,
            db=db,
        )

        script = """
from rgsync import RGJSONWriteBehind, RGJSONWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

connection = MongoConnection('%s', '%s', '172.17.0.1:27017/%s')
db = '%s'

jConnector = MongoConnector(connection, db, 'persons', 'person_id')

RGJSONWriteBehind(GB,  keysPrefix='person',
              connector=jConnector, name='PersonsWriteBehind',
              version='99.99.99')

RGJSONWriteThrough(GB, keysPrefix='__', connector=jConnector,
                   name='JSONWriteThrough', version='99.99.99')

secondConnector = MongoConnector(connection, db, 'secondthings', 'thing_id')
RGJSONWriteBehind(GB,  keysPrefix='thing',
              connector=secondConnector, name='SecondThingWriteBehind',
              version='99.99.99')

RGJSONWriteThrough(GB, keysPrefix='__', connector=secondConnector,
                   name='SecondJSONWriteThrough', version='99.99.99')

""" % (dbuser, dbpasswd, db, db)
        cls.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymongo')

        e = MongoClient(con)

        # # tables are only created upon data use - so this is our equivalent
        # # for mongo
        assert 'version' in e.server_info().keys()
        cls.dbconn = e
        cls.DBNAME = db

   def _sampledata(self):
        d = {'some': 'value',
             'and another': ['set', 'of', 'values']
        }
        return d


   def testSimpleWriteBehind(self):
        self.env.execute_command('json.set', 'person:1', '.', json.dumps(self._sampledata()))
        result = list(self.dbconn[self.DBNAME]['persons'].find())
        while len(result) == 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())

        assert 'gears' not in result[0].keys()
        assert 1 == int(result[0]['person_id'])
        assert 'value' == result[0]['some']
        assert ['set', 'of', 'values'] == result[0]['and another']

        ddd = {"hello": "there", "myname": "is simon!", "well": ["is", "that", "fun"]}
        self.env.execute_command('json.set', 'thing:1', '.', json.dumps(ddd))
        result = list(self.dbconn[self.DBNAME]['secondthings'].find())
        while len(result) == 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['secondthings'].find())

        assert 'gears' not in result[0].keys()
        assert 1 == result[0]['thing_id']
        assert 'there' == result[0]['hello']
        assert ['is', 'that', 'fun'] == result[0]['well']


class TestMongoWithConnectionString(TestMongoJSON):

    @classmethod
    def setup_class(cls):
        cls.env = Redis(decode_responses=True)

        pkg = find_package()

        # connection info
        r = tox.config.parseconfig(open("tox.ini").read())
        docker = r._docker_container_configs["mongo"]["environment"]
        dbuser = docker["MONGO_INITDB_ROOT_USERNAME"]
        dbpasswd = docker["MONGO_INITDB_ROOT_PASSWORD"]
        db = docker["MONGO_DB"]

        con = "mongodb://{user}:{password}@172.17.0.1:27017/".format(
            user=dbuser,
            password=dbpasswd,
        )
        script = """
from rgsync import RGJSONWriteBehind, RGJSONWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

db = '%s'
con = "%s"

connection = MongoConnection(None, None, db, conn_string=con)

jConnector = MongoConnector(connection, db, 'persons', 'person_id')

RGJSONWriteBehind(GB,  keysPrefix='person',
              connector=jConnector, name='PersonsWriteBehind',
              version='99.99.99')

RGJSONWriteThrough(GB, keysPrefix='__', connector=jConnector,
                   name='JSONWriteThrough', version='99.99.99')
""" % (db, con)
        print(script)
        cls.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymongo')

        e = MongoClient(con)

        # # tables are only created upon data use - so this is our equivalent
        # # for mongo
        assert 'version' in e.server_info().keys()
        cls.dbconn = e
        cls.DBNAME = db
