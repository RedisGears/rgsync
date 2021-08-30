import pytest
from collections import OrderedDict
import time
import tox
from redis import Redis
# from RLTest import Env
from pymongo import MongoClient
from tests import find_package, to_utf

@pytest.mark.mongo
class TestMongo:

    @classmethod
    def teardown_class(cls):
        cls.dbconn.drop_database(cls.DBNAME)

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

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__', mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
""" % (dbuser, dbpasswd, db, db)
        cls.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymongo')

        e = MongoClient(con)

        # # tables are only created upon data use - so this is our equivalent
        # # for mongo
        assert 'version' in e.server_info().keys()
        cls.dbconn = e
        cls.DBNAME = db

    def testSimpleWriteBehind(self):
        self.env.flushall()
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22')
        result = list(self.dbconn[self.DBNAME]['persons'].find())
        while len(result) == 0:
            time.sleep(0.1)
            result = list(self.dbconn[self.DBNAME]['persons'].find())

        assert result[0]['first'] == 'foo'
        assert result[0]['last'] == 'bar'
        assert result[0]['age'] == '22'
        assert result[0]['person_id'] == '1'

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

    def testWriteBehindAck(self):
        pass

    def testWriteBehindOperations(self):
        pass

    def testSimpleWriteThrough(self):
        self.env.flushall()

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20')

        res = list(self.dbconn[self.DBNAME]['persons'].find())[0]
        res.pop('_id')
        assert res == {"age": '20', 
                       "last": "bar", 
                       "first": "foo",
                       "person_id": '1'}

        assert OrderedDict(self.env.hgetall("person:1")) == OrderedDict({"age": '20', 
                                                                         "last_name": "bar", 
                                                                         "first_name": "foo"})

        self.env.execute_command('hset __{person:1} # ~')

        # make sure data is deleted from the database
        assert len(list(self.dbconn[self.DBNAME]['persons'].find())) == 0

        assert self.env.hgetall("person:1") == {}


    def testSimpleWriteThroughPartialUpdate(self):
        pass

    def testWriteThroughNoReplicate(self):
        self.env.flushall()

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # +')

        # make sure data is deleted from the database
        assert len(list(self.dbconn[self.DBNAME]['persons'].find())) == 0

        r = self.env.hgetall("person:1")
        assert r == {"age": '20', 
                     "last_name": "bar", 
                     "first_name": "foo"}

    def testDelThroughNoReplicate(self):
        pass

    def testWriteTroughAckStream(self):
        pass

    def testWriteTroughAckStreamNoReplicate(self):
        pass