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

RGJSONWriteBehind(GB,  keysPrefix='person',
              connector=jConnector, name='PersonsWriteBehind', 
              version='99.99.99', dataKey='gears')

RGJSONWriteThrough(GB, keysPrefix='__', connector=jConnector, name='JSONWriteThrough', version='99.99.99')
""" % (dbuser, dbpasswd, db, db)
        cls.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymongo')

        e = MongoClient(con)

        # # tables are only created upon data use - so this is our equivalent
        # # for mongo
        assert 'version' in e.server_info().keys()
        cls.dbconn = e
        cls.DBNAME = db

    def _sampledata(self):
        d = {'redis_data': {
                    'some': 'value', 
                    'and another': ['set', 'of', 'values']
                        }
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

        ud = {'redis_data': {'some': 'not a value!'}}
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

        ud = {'redis_data': {'somerandomthing': 'this too is random!'}}
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
