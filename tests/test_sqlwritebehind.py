from tests import find_package, to_utf
from RLTest import Env
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import tox
import time
import pytest


class BaseSQLTest:

    @classmethod
    def setup_class(cls):
        cls.env = Env()

        pkg = find_package()
        creds = cls.credentials(cls)
        cls.run_install_script(cls, pkg, **creds)

        table_create = """
CREATE TABLE persons (
    person_id VARCHAR(100) NOT NULL, 
    first VARCHAR(100) NOT NULL, last VARCHAR(100) NOT NULL, 
    age INT NOT NULL, 
    PRIMARY KEY (person_id)
);
"""

        e = create_engine(cls.connection(cls, **creds)).execution_options(autocommit=True)
        cls.dbconn = e.connect()
        cls.dbconn.execute(text("DROP TABLE IF EXISTS persons;"))
        cls.dbconn.execute(text(table_create))

    @classmethod
    def teardown_class(cls):
        cls.dbconn.execute(text("DROP TABLE IF EXISTS persons;"))

    def testSimpleWriteBehind(self):
    	self.env.cmd('flushall')
    	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22')
    	result = self.dbconn.execute(text('select * from persons'))
    	while result.rowcount == 0:
    		time.sleep(0.1)
    		result = self.dbconn.execute(text('select * from persons'))
    	res = result.next()
    	self.env.assertEqual(res, ('1', 'foo', 'bar', 22))

    	self.env.cmd('del', 'person:1')
    	result = self.dbconn.execute(text('select * from persons'))
    	count = 0
    	while result.rowcount > 0:
    		time.sleep(0.1)
    		result = self.dbconn.execute(text('select * from persons'))
    		if count == 10:
    			self.env.assertTrue(False, message='Failed on deleting data from the target')
    			break
    		count+=1

    def testWriteBehindAck(self):
    	self.env.cmd('flushall')
    	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '=1')
    	res = None
    	count = 0
    	while res is None:
    		res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
    		if count == 10:
    			self.env.assertTrue(False, message='Failed on deleting data from the target')
    			break
    		count+=1
    	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

    	result = self.dbconn.execute(text('select * from persons'))
    	res = result.next()
    	self.env.assertEqual(res, ('1', 'foo', 'bar', 22))


    	# delete from database
    	self.env.cmd('hset', 'person:1', '#', '~2')
    	res = None
    	count = 0
    	while res is None:
    		res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
    		if count == 10:
    			self.env.assertTrue(False, message='Failed on deleting data from the target')
    			break
    		count+=1
    	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))
    	self.env.expect('hgetall', 'person:1').equal({})
    	result = self.dbconn.execute(text('select * from persons'))
    	self.env.assertEqual(result.rowcount, 0)

    def testWriteBehindOperations(self):
    	self.env.cmd('flushall')

    	# write a hash and not replicate
    	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+')
    	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+1')
    	res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
    	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

    	self.env.expect('hgetall', 'person:1').equal(to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '22'}))

    	# make sure data is not in the database
    	result = self.dbconn.execute(text('select * from persons'))
    	self.env.assertEqual(result.rowcount, 0)

    	# rewrite data with replicate
    	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '=2')
    	res = None
    	count = 0
    	while res is None:
    		res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
    		if count == 10:
    			self.env.assertTrue(False, message='Failed on deleting data from the target')
    			break
    		count+=1
    	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

    	result = self.dbconn.execute(text('select * from persons'))
    	res = result.next()
    	self.env.assertEqual(res, ('1', 'foo', 'bar', 22))

    	# delete data without replicate
    	self.env.cmd('hset', 'person:1', '#', '-')
    	self.env.cmd('hset', 'person:1', '#', '-3')
    	res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}3 0-0')
    	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

    	self.env.expect('hgetall', 'person:1').equal({})

    	# make sure data is still in the dabase
    	result = self.dbconn.execute(text('select * from persons'))
    	res = result.next()
    	self.env.assertEqual(res, ('1', 'foo', 'bar', 22))

    	# rewrite a hash and not replicate
    	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+')
    	self.env.expect('hgetall', 'person:1').equal(to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '22'}))

    	# delete data with replicate and make sure its deleted from database and from redis
    	self.env.cmd('hset', 'person:1', '#', '~')
    	result = self.dbconn.execute(text('select * from persons'))
    	count = 0
    	while result.rowcount > 0:
    		time.sleep(0.1)
    		result = self.dbconn.execute(text('select * from persons'))
    		if count == 10:
    			self.env.assertTrue(False, message='Failed on deleting data from the target')
    			break
    		count+=1
    	self.env.expect('hgetall', 'person:1').equal({})

    def testSimpleWriteThrough(self):
        self.env.cmd('flushall')

        self.env.cmd('hset __{person:1} first_name foo last_name bar age 20')

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.next()
        self.env.assertEqual(res, ('1', 'foo', 'bar', 20))

        self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

        self.env.cmd('hset __{person:1} # ~')

        # make sure data is deleted from the database
        result = self.dbconn.execute(text('select * from persons'))
        self.env.assertEqual(result.rowcount, 0)

        self.env.expect('hgetall', 'person:1').equal({})

    def testSimpleWriteThroughPartialUpdate(self):
        self.env.cmd('flushall')

        self.env.cmd('hset __{person:1} first_name foo last_name bar age 20')

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.next()
        self.env.assertEqual(res, ('1', 'foo', 'bar', 20))

        self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

        self.env.cmd('hset __{person:1} first_name foo1')

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.next()
        self.env.assertEqual(res, ('1', 'foo1', 'bar', 20))

        self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo1'}))

        self.env.cmd('hset __{person:1} # ~')

        # make sure data is deleted from the database
        result = self.dbconn.execute(text('select * from persons'))
        self.env.assertEqual(result.rowcount, 0)

        self.env.expect('hgetall', 'person:1').equal({})

    def testWriteThroughNoReplicate(self):
        self.env.cmd('flushall')

        self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # +')

        # make sure data is deleted from the database
        result = self.dbconn.execute(text('select * from persons'))
        self.env.assertEqual(result.rowcount, 0)

        self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

    def testDelThroughNoReplicate(self):
        self.env.cmd('flushall')

        self.env.cmd('hset __{person:1} first_name foo last_name bar age 20')

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.next()
        self.env.assertEqual(res, ('1', 'foo', 'bar', 20))

        self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

        self.env.cmd('hset __{person:1} # -')

        # make sure data was deleted from redis but not from the target
        self.env.expect('hgetall', 'person:1').equal({})
        result = self.dbconn.execute(text('select * from persons'))
        res = result.next()
        self.env.assertEqual(res, ('1', 'foo', 'bar', 20))


        self.env.cmd('hset __{person:1} # ~')

        # make sure data was deleted from target as well
        result = self.dbconn.execute(text('select * from persons'))
        self.env.assertEqual(result.rowcount, 0)

    def testWriteTroughAckStream(self):
        self.env.cmd('flushall')

        self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # =1')

        res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
        self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.next()
        self.env.assertEqual(res, ('1', 'foo', 'bar', 20))

        # make sure data is in redis
        self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

        self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # ~2')

        res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
        self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

        # make sure data is deleted from the database
        result = self.dbconn.execute(text('select * from persons'))
        self.env.assertEqual(result.rowcount, 0)

        self.env.expect('hgetall', 'person:1').equal({})

    def testWriteTroughAckStreamNoReplicate(self):
        self.env.cmd('flushall')

        self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # +1')

        res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
        self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

        # make sure data is not in the target
        result = self.dbconn.execute(text('select * from persons'))
        self.env.assertEqual(result.rowcount, 0)

        # make sure data is in redis
        self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

        self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # -2')

        res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
        self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

        # make sure data is deleted from redis
        self.env.expect('hgetall', 'person:1').equal({})

@pytest.mark.postgres
class TestPostgresql(BaseSQLTest):

    def credentials(self):
        r = tox.config.parseconfig(open("tox.ini").read())
        docker = r._docker_container_configs["postgres"]["environment"]
        dbuser = docker["POSTGRES_USER"]
        dbpasswd = docker["POSTGRES_PASSWORD"]
        db = docker["POSTGRES_DB"]

        return {"dbuser": dbuser, 
                "dbpasswd": dbpasswd, 
                "db": db}

    def connection(self, **kwargs):

        con = 'postgresql://{user}:{password}@172.17.0.1:5432/{db}'.format(
            user=kwargs['dbuser'],
            password=kwargs['dbpasswd'],
            db=kwargs['db'],
        )
        return con

    def run_install_script(self, pkg, **kwargs):
        script = """
from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import PostgresConnector, PostgresConnection

connection = PostgresConnection('%s', '%s', '127.17.0.1:5432/%s')
personsConnector = PostgresConnector(connection, 'persons', 'person_id')

personsMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')
RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
""" % (kwargs['dbuser'], kwargs['dbpasswd'], kwargs['db'])
        self.env.cmd('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'psycopg2-binary')

@pytest.mark.sqlite
class TestSQLite(BaseSQLTest):
    def credentials(self):
        import tempfile
        return {'db': tempfile.mktemp()}

    def connection(self, **kwargs):
        pass
        con = "sqlite:///%s" % kwargs['db']
        return con

    def run_install_script(self, pkg, **kwargs):
        # initial gears setup
        script = """
from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import SQLiteConnector, SQLiteConnection

connection = SQLiteConnection('%s')

personsConnector = SQLiteConnector(connection, 'persons', 'person_id')

personsMappings = {
    'first_name':'first',
    'last_name':'last',
    'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
""" % kwargs['db']
        self.env.cmd('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg)

@pytest.mark.mysql
class TestMysql(BaseSQLTest):

    def credentials(self):
        r = tox.config.parseconfig(open("tox.ini").read())
        docker = r._docker_container_configs["mysql"]["environment"]
        dbuser = docker["MYSQL_USER"]
        dbpasswd = docker["MYSQL_PASSWORD"]
        db = docker["MYSQL_DATABASE"]

        return {"dbuser": dbuser, 
                "dbpasswd": dbpasswd, 
                "db": db}


    def connection(self, **kwargs):

        # connection info

        con = 'mysql+pymysql://{user}:{password}@172.17.0.1:3306/{db}'.format(
            user=kwargs['dbuser'],
            password=kwargs['dbpasswd'],
            db=kwargs['db'],
        )

        return con

    def run_install_script(self, pkg, **kwargs):
        # initial gears setup
        script = """
from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import MySqlConnector, MySqlConnection

connection = MySqlConnection('%s', '%s', '172.17.0.1:3306/%s')

personsConnector = MySqlConnector(connection, 'persons', 'person_id')

personsMappings = {
    'first_name':'first',
    'last_name':'last',
    'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
""" % (kwargs['dbuser'], kwargs['dbpasswd'], kwargs['db'])
        self.env.cmd('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymysql[rsa]')