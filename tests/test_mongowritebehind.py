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
class TestMongo:

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
from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

connection = MongoConnection('%s', '%s', '172.17.0.1:27017/%s')
db = '%s'

personsConnector = MongoConnector(connection, db, 'persons', 'person_id')

personsMappings = {
    'first_name':'first',
    'last_name':'last',
    'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, 
              connector=personsConnector, name='PersonsWriteBehind', 
              version='99.99.99')

RGWriteThrough(GB, keysPrefix='__', mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
""" % (dbuser, dbpasswd, db, db)
        cls.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymongo')

        e = MongoClient(con)

        # # tables are only created upon data use - so this is our equivalent
        # # for mongo
        assert 'version' in e.server_info().keys()
        cls.dbconn = e
        cls.DBNAME = db

    # def testSimpleWriteBehind(self):
    #     self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22')
    #     result = list(self.dbconn[self.DBNAME]['persons'].find())
    #     while len(result) == 0:
    #         time.sleep(0.1)
    #         result = list(self.dbconn[self.DBNAME]['persons'].find())

    #     assert result[0]['first'] == 'foo'
    #     assert result[0]['last'] == 'bar'
    #     assert result[0]['age'] == '22'
    #     assert result[0]['person_id'] == '1'

    #     self.env.execute_command('del', 'person:1')
    #     result = list(self.dbconn[self.DBNAME]['persons'].find())
    #     count = 0
    #     while len(result) != 0:
    #         time.sleep(0.1)
    #         result = list(self.dbconn[self.DBNAME]['persons'].find())
    #         if count == 10:
    #             assert False == True, "Failed deleting data from mongo"
    #             break
    #         count += 1

    def testWriteBehindAck(self):
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '=1')
        res = None
        count = 0
        while res is None:
            res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
            if count == 10:
                assert False == True, "Failed deleting data from mongo"
                break
            count+=1
        assert res[0][1][0][1], ['status', 'done']

        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        res.pop('_id')
        assert res == {"age": 22, 
                      "last": "bar", 
                      "first": "foo",
                      "person_id": 1}

        # # delete from database
        self.env.execute_command('hset', 'person:1', '#', '~2')
        res = None
        count = 0
        while res is None:
            res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
            if count == 10:
                self.env.assertTrue(False, message='Failed on deleting data from the target')
                break
            count+=1
        assert res[0][1][0][1], ['status', 'done']
        assert self.env.hgetall("person:1") == {}
        assert len(list(self.dbconn[self.DBNAME]['persons'].find())) == 0

    def testWriteBehindOperations(self):
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+')
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+1')
        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
        assert res[0][1][0][1], ['status', 'done']

        assert self.env.hgetall('person:1') == {'age': '22', 'last_name': 'bar', 'first_name': 'foo'}
 
        assert len(list(self.dbconn[self.DBNAME]['persons'].find())) == 0

        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '=2')
        res = None
        count = 0
        while res is None:
            res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
            if count == 10:
                assert False == True, "Failed deleting data from mongo"
                break
            count+=1
        assert res[0][1][0][1], ['status', 'done']

        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        res.pop("_id")
        assert res == {"age": 22, 
                      "last": "bar", 
                      "first": "foo",
                      "person_id": 1}

        # delete data without replicate
        self.env.execute_command('hset', 'person:1', '#', '-')
        self.env.execute_command('hset', 'person:1', '#', '-3')
        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}3 0-0')
        assert res[0][1][0][1], ['status', 'done']

        assert self.env.hgetall('person:1') == {}


        # make sure data is still in the dabase
        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        res.pop("_id")
        assert res == {"age": 22, 
                      "last": "bar", 
                      "first": "foo",
                      "person_id": 1}

        # rewrite a hash and not replicate
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+')
        assert self.env.hgetall('person:1') == {'first_name':'foo', 'last_name': 'bar', 'age': '22'}

        # delete data with replicate and make sure its deleted from database and from redis
        self.env.execute_command('hset', 'person:1', '#', '~')
        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        count = 0
        while len(res) != 0:
            time.sleep(0.1)
            res = list(self.dbconn[self.DBNAME]['persons'].find())
            if count == 10:
                assert False == True, "Failed deleting data from mongo"
                break
            count+=1
        assert self.env.hgetall('person:1') == {}


    def testSimpleWriteThrough(self):

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20')

        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        res.pop('_id')
        assert res == {"age": 20, 
                       "last": "bar", 
                       "first": "foo",
                       "person_id": 1}

        assert OrderedDict(self.env.hgetall("person:1")) == OrderedDict({"age": '20', 
                                                                         "last_name": "bar", 
                                                                         "first_name": "foo"})

        self.env.execute_command('hset __{person:1} # ~')

        # make sure data is deleted from the database
        assert len(list(self.dbconn[self.DBNAME]['persons'].find())) == 0

        assert self.env.hgetall("person:1") == {}


    def testSimpleWriteThroughPartialUpdate(self):

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20')
        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        res.pop('_id')
        assert res == {"age": 20,
                       "last": "bar", 
                       "first": "foo",
                       "person_id": 1}

        self.env.execute_command('hset __{person:1} first_name foo1')
        print(list(self.dbconn[self.DBNAME]['persons'].find()))
        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        assert res['first'] == 'foo1'

        r = self.env.hgetall("person:1")
        assert r == {"age": '20', 
                     "last_name": "bar", 
                     "first_name": "foo1"}

        self.env.execute_command('hset __{person:1} # ~')

        # make sure data is deleted from the database
        assert len(list(self.dbconn[self.DBNAME]['persons'].find())) == 0

        assert self.env.hgetall('person:1') == {}


    def testWriteThroughNoReplicate(self):

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # +')

        # make sure data is deleted from the database
        assert len(list(self.dbconn[self.DBNAME]['persons'].find())) == 0

        r = self.env.hgetall("person:1")
        assert r == {"age": '20',
                     "last_name": "bar", 
                     "first_name": "foo"}

    def testDelThroughNoReplicate(self):

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20')
        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        res.pop('_id')
        assert res == {"age": 20, 
                       "last": "bar", 
                       "first": "foo",
                       "person_id": 1}

        # make sure data is in the dabase

        assert OrderedDict(self.env.hgetall("person:1")) == OrderedDict({"age": '20', 
                                                                         "last_name": "bar", 
                                                                         "first_name": "foo"})

        self.env.execute_command('hset __{person:1} # -')

        # make sure data was deleted from redis but not from the target
        assert self.env.hgetall("person:1") == {}
        result = list(self.dbconn[self.DBNAME]['persons'].find())
        assert len(result) != 0

        self.env.execute_command('hset __{person:1} # ~')

        # make sure data was deleted from target as well
        result = list(self.dbconn[self.DBNAME]['persons'].find())
        assert len(result) == 0

    def testWriteTroughAckStream(self):

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # =1')

        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
        assert res[0][1][0][1], ['status', 'done']

        # make sure data is in the dabase
        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        res.pop("_id")
        assert res == {"age": 20, 
                      "last": "bar", 
                      "first": "foo",
                      "person_id": 1}

        # make sure data is in redis
        assert self.env.hgetall('person:1') == {'age': '20', 'last_name': 'bar', 'first_name': 'foo'}

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # ~2')

        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
        assert res[0][1][0][1], ['status', 'done']

        # make sure data is deleted from the database
        res = list(self.dbconn[self.DBNAME]['persons'].find())
        assert len(res) == 0

        assert self.env.hgetall("person:1") == {}

    def testWriteTroughAckStreamNoReplicate(self):

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # +1')

        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
        assert res[0][1][0][1], ['status', 'done']

        # make sure data is not in the target
        res = list(self.dbconn[self.DBNAME]['persons'].find())
        assert len(res) == 0

        # make sure data is in redis
        assert self.env.hgetall('person:1') == {'age': '20', 'last_name': 'bar', 'first_name': 'foo'}

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # -2')

        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
        assert res[0][1][0][1] == ['status', 'done']

        # make sure data is deleted from redis
        assert self.env.hgetall("person:1") == {}


@pytest.mark.mongojson
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

jMappings = {
    'redis_data':'gears',
}

RGJSONWriteBehind(GB,  keysPrefix='person', mappings=jMappings, 
              connector=jConnector, name='PersonsWriteBehind', 
              version='99.99.99')

RGJSONWriteThrough(GB, keysPrefix='__', mappings=jMappings, connector=jConnector, name='JSONWriteThrough', version='99.99.99')
""" % (dbuser, dbpasswd, db, db)
        cls.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymongo')

        e = MongoClient(con)

        # # tables are only created upon data use - so this is our equivalent
        # # for mongo
        assert 'version' in e.server_info().keys()
        cls.dbconn = e
        cls.DBNAME = db

    def _sampledata(self, somedict={}):
        d = {'redis_data': 
                        {'some': 'value', 
                         'and another': ['set', 'of', 'values']
                        }
               }
        d.update(somedict)
        return d
        
    def testSimpleWriteBehind(self):
        self.env.execute_command('json.set', 'person:1', '.', json.dumps(self._sampledata()))
        result = list(self.dbconn[self.DBNAME]['persons'].find())
        while len(result) == 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())

        assert 'person_id' in result[0].keys()
        assert 'gears' in result[0].keys()
        assert 'value' == result[0]['gears']['some']
        assert ['set', 'of', 'values'] == result[0]['gears']['and another']

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

    def testSimpleWriteThroughPartialUpdate(self):

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20')
        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        res.pop('_id')
        assert res == {"age": '20', 
                       "last": "bar", 
                       "first": "foo",
                       "person_id": '1'}

        self.env.execute_command('hset __{person:1} first_name foo1')
        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        assert res['first'] == 'foo1'

        r = self.env.hgetall("person:1")
        assert r == {"age": '20', 
                     "last_name": "bar", 
                     "first_name": "foo1"}

        self.env.execute_command('hset __{person:1} # ~')

        # make sure data is deleted from the database
        assert len(list(self.dbconn[self.DBNAME]['persons'].find())) == 0

        assert self.env.hgetall('person:1') == {}