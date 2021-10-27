import pytest
import json
from collections import OrderedDict
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

dataKey = 'gears'
RGJSONWriteBehind(GB,  keysPrefix='person',
              connector=jConnector, name='PersonsWriteBehind', 
              version='99.99.99', dataKey=dataKey)

RGJSONWriteThrough(GB, keysPrefix='__', connector=jConnector, 
                   name='JSONWriteThrough', version='99.99.99', dataKey=dataKey)
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
        while len(result) == 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())

        assert 'gears' in result[0].keys()
        assert '1' == result[0]['person_id']
        assert 'value' == result[0]['gears']['some']
        assert ['set', 'of', 'values'] == result[0]['gears']['and another']
       
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
            if result[0]['gears']['some'] == 'not a value!':
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
            if 'somerandomthing' not in result[0]['gears'].keys():
                count += 1
            else:
                assert result[0]['gears']['somerandomthing'] == 'this too is random!'
                break

        if count == 10:
            assert False == True, "Failed to update sub value!"

        assert result[0]['person_id'] == '1'


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

dataKey = 'gears'
RGJSONWriteBehind(GB,  keysPrefix='person',
              connector=jConnector, name='PersonsWriteBehind', 
              version='99.99.99', dataKey=dataKey)

RGJSONWriteThrough(GB, keysPrefix='__', connector=jConnector, 
                   name='JSONWriteThrough', version='99.99.99', dataKey=dataKey)

secondConnector = MongoConnector(connection, db, 'secondthings', 'thing_id')
RGJSONWriteBehind(GB,  keysPrefix='thing',
              connector=secondConnector, name='SecondThingWriteBehind', 
              version='99.99.99', dataKey=dataKey)

RGJSONWriteThrough(GB, keysPrefix='__', connector=secondConnector, 
                   name='SecondJSONWriteThrough', version='99.99.99', dataKey=dataKey)

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

        assert 'gears' in result[0].keys()
        assert '1' == result[0]['person_id']
        assert 'value' == result[0]['gears']['some']
        assert ['set', 'of', 'values'] == result[0]['gears']['and another']
       
        ddd = {"hello": "there", "myname": "is simon!", "well": ["is", "that", "fun"]}
        self.env.execute_command('json.set', 'thing:1', '.', json.dumps(ddd))
        result = list(self.dbconn[self.DBNAME]['secondthings'].find())
        while len(result) == 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['secondthings'].find())

        assert 'gears' in result[0].keys()
        assert 1 == result[0]['thing_id']
        assert 'there' == result[0]['gears']['hello']
        assert ['is', 'that', 'fun'] == result[0]['gears']['well']
       