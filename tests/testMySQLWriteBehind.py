from RLTest import Env
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import time
import pytest
import tox


def to_utf(d):
    if isinstance(d, str):
        return d.encode('utf-8')
    if isinstance(d, dict):
        return {to_utf(k): to_utf(v) for k, v in d.items()}
    if isinstance(d, list):
        return [to_utf(x) for x in d]
    return d

# @pytest.fixture
# def client():
#     e = Env()
#     r = tox.config.parseconfig(open("tox.ini").read())
#     docker = r._docker_container_configs["toxmysql"]["environment"]
#     con = 'mysql+pymysql://{user}:{password}@localhost:3306/{db}'.format(
#         user=docker['MYSQL_USER'], 
#         password=docker['MYSQL_PASSWORD'],
#         db=docker['MYSQL_DATABASE'],
#     )
#     e = create_engine(con).execution_options(autocommit=True)

#     return e.connect()

# @pytest.mark.mysql
# def test_simplewritebehind(client):
#     client.execute(text('delete from test.persons'))

@pytest.mark.mysql
class TestMysql:

    @classmethod
    def setup_class(cls):
        env = Env()
        cls.env = Env()

        r = tox.config.parseconfig(open("tox.ini").read())
        docker = r._docker_container_configs["toxmysql"]["environment"]
        dbuser = docker["MYSQL_USER"]
        dbpasswd = docker["MYSQL_PASSWORD"]
        db = docker["MYSQL_DATABASE"]
        script = """
from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import MySqlConnector, MySqlConnection

'''
Create MySQL connection object
'''
connection = MySqlConnection({user}, {password}, '127.0.0.1:3306/{db}')

'''
Create MySQL persons connector
'''
personsConnector = MySqlConnector(connection, 'persons', 'person_id')

personsMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
""".format(user=dbuser, password=dbpasswd, db=db)

        # self.dbConn.execute(text('delete from test.persons'))


        cls.env.cmd('RG.PYEXECUTE', script, 'REQUIREMENTS', 'pymysql')
        con = 'mysql+pymysql://{user}:{password}@localhost:3306/{db}'.format(
            user=dbuser,
            password=dbpasswd,
            db=db,
        )
        e = create_engine(con).execution_options(autocommit=True)
        cls.dbconn = e.connect()
        cls.dbconn.execute(text('delete from test.persons'))

    def testSimpleWriteBehind(self):
    	self.env.cmd('flushall')
    	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22')
    	result = self.dbconn.execute(text('select * from test.persons'))
    	while result.rowcount == 0:
    		time.sleep(0.1)
    		result = self.dbconn.execute(text('select * from test.persons'))
    	res = result.next()
    	self.env.assertEqual(res, ('1', 'foo', 'bar', 22))

    	self.env.cmd('del', 'person:1')
    	result = self.dbconn.execute(text('select * from test.persons'))
    	count = 0
    	while result.rowcount > 0:
    		time.sleep(0.1)
    		result = self.dbconn.execute(text('select * from test.persons'))
    		if count == 10:
    			self.env.assertTrue(False, message='Failed on deleting data from the target')
    			break
    		count+=1


# def Connect():
#     ConnectionStr = 'mysql+pymysql://{user}:{password}@{db}'.format(user='demouser', password='Password123!', db='localhost:3306/test')
#     engine = create_engine(ConnectionStr).execution_options(autocommit=True)
#     conn = engine.connect()
#     return conn

# class testWriteBehind:
#     def __init__(self):
#         self.env = Env()
#         f = open('./examples/mysql/example.py', 'rt')
#         script = f.read()
#         f.close()
#         self.env.cmd('RG.PYEXECUTE', script, 'REQUIREMENTS', 'pymysql')

#         self.dbConn = Connect()
#         self.dbConn.execute(text('delete from test.persons'))

#     def testSimpleWriteBehind(self):
#     	self.env.cmd('flushall')
#     	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22')
#     	result = self.dbConn.execute(text('select * from test.persons'))
#     	while result.rowcount == 0:
#     		time.sleep(0.1)
#     		result = self.dbConn.execute(text('select * from test.persons'))
#     	res = result.next()
#     	self.env.assertEqual(res, ('1', 'foo', 'bar', 22))

#     	self.env.cmd('del', 'person:1')
#     	result = self.dbConn.execute(text('select * from test.persons'))
#     	count = 0
#     	while result.rowcount > 0:
#     		time.sleep(0.1)
#     		result = self.dbConn.execute(text('select * from test.persons'))
#     		if count == 10:
#     			self.env.assertTrue(False, message='Failed on deleting data from the target')
#     			break
#     		count+=1

#     def testWriteBehindAck(self):
#     	self.env.cmd('flushall')
#     	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '=1')
#     	res = None
#     	count = 0
#     	while res is None:
#     		res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
#     		if count == 10:
#     			self.env.assertTrue(False, message='Failed on deleting data from the target')
#     			break
#     		count+=1
#     	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

#     	result = self.dbConn.execute(text('select * from test.persons'))
#     	res = result.next()
#     	self.env.assertEqual(res, ('1', 'foo', 'bar', 22))


#     	# delete from database
#     	self.env.cmd('hset', 'person:1', '#', '~2')
#     	res = None
#     	count = 0
#     	while res is None:
#     		res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
#     		if count == 10:
#     			self.env.assertTrue(False, message='Failed on deleting data from the target')
#     			break
#     		count+=1
#     	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))
#     	self.env.expect('hgetall', 'person:1').equal({})
#     	result = self.dbConn.execute(text('select * from test.persons'))
#     	self.env.assertEqual(result.rowcount, 0)

#     def testWriteBehindOperations(self):
#     	self.env.cmd('flushall')

#     	# write a hash and not replicate
#     	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+')
#     	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+1')
#     	res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
#     	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

#     	self.env.expect('hgetall', 'person:1').equal(to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '22'}))

#     	# make sure data is not in the database
#     	result = self.dbConn.execute(text('select * from test.persons'))
#     	self.env.assertEqual(result.rowcount, 0)

#     	# rewrite data with replicate
#     	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '=2')
#     	res = None
#     	count = 0
#     	while res is None:
#     		res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
#     		if count == 10:
#     			self.env.assertTrue(False, message='Failed on deleting data from the target')
#     			break
#     		count+=1
#     	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

#     	result = self.dbConn.execute(text('select * from test.persons'))
#     	res = result.next()
#     	self.env.assertEqual(res, ('1', 'foo', 'bar', 22))

#     	# delete data without replicate
#     	self.env.cmd('hset', 'person:1', '#', '-')
#     	self.env.cmd('hset', 'person:1', '#', '-3')
#     	res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}3 0-0')
#     	self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

#     	self.env.expect('hgetall', 'person:1').equal({})

#     	# make sure data is still in the dabase
#     	result = self.dbConn.execute(text('select * from test.persons'))
#     	res = result.next()
#     	self.env.assertEqual(res, ('1', 'foo', 'bar', 22))

#     	# rewrite a hash and not replicate
#     	self.env.cmd('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+')
#     	self.env.expect('hgetall', 'person:1').equal(to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '22'}))

#     	# delete data with replicate and make sure its deleted from database and from redis
#     	self.env.cmd('hset', 'person:1', '#', '~')
#     	result = self.dbConn.execute(text('select * from test.persons'))
#     	count = 0
#     	while result.rowcount > 0:
#     		time.sleep(0.1)
#     		result = self.dbConn.execute(text('select * from test.persons'))
#     		if count == 10:
#     			self.env.assertTrue(False, message='Failed on deleting data from the target')
#     			break
#     		count+=1
#     	self.env.expect('hgetall', 'person:1').equal({})

#     def testSimpleWriteThrough(self):
#         self.env.cmd('flushall')

#         self.env.cmd('hset __{person:1} first_name foo last_name bar age 20')

#         # make sure data is in the dabase
#         result = self.dbConn.execute(text('select * from test.persons'))
#         res = result.next()
#         self.env.assertEqual(res, ('1', 'foo', 'bar', 20))

#         self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

#         self.env.cmd('hset __{person:1} # ~')

#         # make sure data is deleted from the database
#         result = self.dbConn.execute(text('select * from test.persons'))
#         self.env.assertEqual(result.rowcount, 0)

#         self.env.expect('hgetall', 'person:1').equal({})

#     def testSimpleWriteThroughPartialUpdate(self):
#         self.env.cmd('flushall')

#         self.env.cmd('hset __{person:1} first_name foo last_name bar age 20')

#         # make sure data is in the dabase
#         result = self.dbConn.execute(text('select * from test.persons'))
#         res = result.next()
#         self.env.assertEqual(res, ('1', 'foo', 'bar', 20))

#         self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

#         self.env.cmd('hset __{person:1} first_name foo1')

#         # make sure data is in the dabase
#         result = self.dbConn.execute(text('select * from test.persons'))
#         res = result.next()
#         self.env.assertEqual(res, ('1', 'foo1', 'bar', 20))

#         self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo1'}))

#         self.env.cmd('hset __{person:1} # ~')

#         # make sure data is deleted from the database
#         result = self.dbConn.execute(text('select * from test.persons'))
#         self.env.assertEqual(result.rowcount, 0)

#         self.env.expect('hgetall', 'person:1').equal({})

#     def testWriteThroughNoReplicate(self):
#         self.env.cmd('flushall')

#         self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # +')

#         # make sure data is deleted from the database
#         result = self.dbConn.execute(text('select * from test.persons'))
#         self.env.assertEqual(result.rowcount, 0)

#         self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

#     def testDelThroughNoReplicate(self):
#         self.env.cmd('flushall')

#         self.env.cmd('hset __{person:1} first_name foo last_name bar age 20')

#         # make sure data is in the dabase
#         result = self.dbConn.execute(text('select * from test.persons'))
#         res = result.next()
#         self.env.assertEqual(res, ('1', 'foo', 'bar', 20))

#         self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

#         self.env.cmd('hset __{person:1} # -')

#         # make sure data was deleted from redis but not from the target
#         self.env.expect('hgetall', 'person:1').equal({})
#         result = self.dbConn.execute(text('select * from test.persons'))
#         res = result.next()
#         self.env.assertEqual(res, ('1', 'foo', 'bar', 20))


#         self.env.cmd('hset __{person:1} # ~')

#         # make sure data was deleted from target as well
#         result = self.dbConn.execute(text('select * from test.persons'))
#         self.env.assertEqual(result.rowcount, 0)

#     def testWriteTroughAckStream(self):
#         self.env.cmd('flushall')

#         self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # =1')

#         res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
#         self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

#         # make sure data is in the dabase
#         result = self.dbConn.execute(text('select * from test.persons'))
#         res = result.next()
#         self.env.assertEqual(res, ('1', 'foo', 'bar', 20))

#         # make sure data is in redis
#         self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

#         self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # ~2')

#         res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
#         self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

#         # make sure data is deleted from the database
#         result = self.dbConn.execute(text('select * from test.persons'))
#         self.env.assertEqual(result.rowcount, 0)

#         self.env.expect('hgetall', 'person:1').equal({})

#     def testWriteTroughAckStreamNoReplicate(self):
#         self.env.cmd('flushall')

#         self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # +1')

#         res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
#         self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

#         # make sure data is not in the target
#         result = self.dbConn.execute(text('select * from test.persons'))
#         self.env.assertEqual(result.rowcount, 0)

#         # make sure data is in redis
#         self.env.expect('hgetall', 'person:1').equal(to_utf({'age': '20', 'last_name': 'bar', 'first_name': 'foo'}))

#         self.env.cmd('hset __{person:1} first_name foo last_name bar age 20 # -2')

#         res = self.env.cmd('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
#         self.env.assertEqual(res[0][1][0][1], to_utf(['status', 'done']))

#         # make sure data is deleted from redis
#         self.env.expect('hgetall', 'person:1').equal({})
