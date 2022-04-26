from tests import find_package, to_utf
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import tox
import time
import pytest


class BaseSQLTest:

    @classmethod
    def setup_class(cls):
        cls.env = Redis(decode_responses=True)

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
        cls.dbconn.execute(text("DROP TABLE IF EXISTS persons"))
        cls.dbconn.execute(text(table_create))

    @classmethod
    def teardown_class(cls):
        cls.dbconn.execute(text("DROP TABLE IF EXISTS persons"))
        cls.env.flushall()
        
    def testSimpleWriteBehind(self):
        self.env.execute_command('flushall')
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22')
        result = self.dbconn.execute(text('select * from persons'))
        count = 0
        while result.rowcount in [0, -1]:
            time.sleep(0.3)
            result = self.dbconn.execute(text('select * from persons'))
            count += 1
            if count == 10:
                break
        res = result.fetchone()
        assert res == ('1', 'foo', 'bar', 22)

        self.env.execute_command('del', 'person:1')
        result = self.dbconn.execute(text('select * from persons'))
        count = 0
        while result.rowcount > 0:
            time.sleep(0.1)
            result = self.dbconn.execute(text('select * from persons'))
            if count == 10:
                assert True == False, 'Failed on deleting data from the target'
                break
            count+=1

    def testWriteBehindAck(self):
        self.env.execute_command('flushall')
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '=1')
        res = None
        count = 0
        while res is None:
            res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
            if count == 10:
                assert True == False, 'Failed on deleting data from the target'
                break
            count+=1
        assert res[0][1][0][1] == to_utf(['status', 'done'])

        result = self.dbconn.execute(text('select * from persons'))
        res = result.fetchone()
        assert res == ('1', 'foo', 'bar', 22)


        # delete from database
        self.env.execute_command('hset', 'person:1', '#', '~2')
        res = None
        count = 0
        while res is None:
            res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
            if count == 10:
                assert True == False, 'Failed on deleting data from the target'
                break
            count+=1
        assert res[0][1][0][1] == to_utf(['status', 'done'])
        assert self.env.execute_command('hgetall', 'person:1') == {}
        result = self.dbconn.execute(text('select * from persons'))
        assert result.rowcount in [0, -1]

    def testWriteBehindOperations(self):
        self.env.execute_command('flushall')

        # write a hash and not replicate
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+')
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+1')
        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
        assert res[0][1][0][1] == to_utf(['status', 'done'])

        assert self.env.execute_command('hgetall', 'person:1') == to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '22'})

        # make sure data is not in the database
        result = self.dbconn.execute(text('select * from persons'))
        assert result.rowcount in [0, -1]

        # rewrite data with replicate
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '=2')
        res = None
        count = 0
        while res is None:
            res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
            if count == 10:
                assert True == False, 'Failed on deleting data from the target'
                break
            count+=1
        assert res[0][1][0][1] == to_utf(['status', 'done'])

        result = self.dbconn.execute(text('select * from persons'))
        res = result.fetchone()
        assert res == ('1', 'foo', 'bar', 22)

        # delete data without replicate
        self.env.execute_command('hset', 'person:1', '#', '-')
        self.env.execute_command('hset', 'person:1', '#', '-3')
        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}3 0-0')
        assert res[0][1][0][1] == to_utf(['status', 'done'])

        assert self.env.execute_command('hgetall', 'person:1') == {}

        # make sure data is still in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.fetchone()
        assert res == ('1', 'foo', 'bar', 22)

        # rewrite a hash and not replicate
        self.env.execute_command('hset', 'person:1', 'first_name', 'foo', 'last_name', 'bar', 'age', '22', '#', '+')
        assert self.env.execute_command('hgetall', 'person:1') == to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '22'})

        # delete data with replicate and make sure its deleted from database and from redis
        self.env.execute_command('hset', 'person:1', '#', '~')
        result = self.dbconn.execute(text('select * from persons'))
        count = 0
        while result.rowcount > 0:
            time.sleep(0.1)
            result = self.dbconn.execute(text('select * from persons'))
            if count == 10:
                assert True == False, 'Failed on deleting data from the target'
                break
            count+=1
        assert self.env.execute_command('hgetall', 'person:1') == {}

    def testSimpleWriteThrough(self):
        self.env.execute_command('flushall')

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20')

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.fetchone()
        assert res == ('1', 'foo', 'bar', 20)

        assert self.env.execute_command('hgetall', 'person:1') == to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '20'})

        self.env.execute_command('hset __{person:1} # ~')

        # make sure data is deleted from the database
        result = self.dbconn.execute(text('select * from persons'))
        assert result.rowcount in [0, -1]

        assert self.env.execute_command('hgetall', 'person:1') == {}

    def testSimpleWriteThroughPartialUpdate(self):
        self.env.execute_command('flushall')

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20')

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.fetchone()
        assert res == ('1', 'foo', 'bar', 20)

        assert self.env.execute_command('hgetall', 'person:1') == to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '20'})

        self.env.execute_command('hset __{person:1} first_name foo1')

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.fetchone()
        assert res == ('1', 'foo1', 'bar', 20)

        assert self.env.execute_command('hgetall', 'person:1') == to_utf({'first_name':'foo1', 'last_name': 'bar', 'age': '20'})

        self.env.execute_command('hset __{person:1} # ~')

        # make sure data is deleted from the database
        result = self.dbconn.execute(text('select * from persons'))
        assert result.rowcount in [0, -1]

        assert self.env.execute_command('hgetall', 'person:1') == {}

    def testWriteThroughNoReplicate(self):
        self.env.execute_command('flushall')

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # +')

        # make sure data is deleted from the database
        result = self.dbconn.execute(text('select * from persons'))
        assert result.rowcount in [0, -1]

        assert self.env.execute_command('hgetall', 'person:1') == to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '20'})

    def testDelThroughNoReplicate(self):
        self.env.execute_command('flushall')

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20')

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.fetchone()
        assert res == ('1', 'foo', 'bar', 20)

        assert self.env.execute_command('hgetall', 'person:1') == to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '20'})

        self.env.execute_command('hset __{person:1} # -')

        # make sure data was deleted from redis but not from the target
        assert self.env.execute_command('hgetall', 'person:1') == {}
        result = self.dbconn.execute(text('select * from persons'))
        res = result.fetchone()
        assert res == ('1', 'foo', 'bar', 20)


        self.env.execute_command('hset __{person:1} # ~')

        # make sure data was deleted from target as well
        result = self.dbconn.execute(text('select * from persons'))
        assert result.rowcount in [0, -1]

    def testWriteTroughAckStream(self):
        self.env.execute_command('flushall')

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # =1')

        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
        assert res[0][1][0][1] == to_utf(['status', 'done'])

        # make sure data is in the dabase
        result = self.dbconn.execute(text('select * from persons'))
        res = result.fetchone()
        assert res == ('1', 'foo', 'bar', 20)

        # make sure data is in redis
        assert self.env.execute_command('hgetall', 'person:1') == to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '20'})

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # ~2')

        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
        assert res[0][1][0][1] == to_utf(['status', 'done'])

        # make sure data is deleted from the database
        result = self.dbconn.execute(text('select * from persons'))
        assert result.rowcount in [0, -1]

        assert self.env.execute_command('hgetall', 'person:1') == {}

    def testWriteTroughAckStreamNoReplicate(self):
        self.env.execute_command('flushall')

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # +1')

        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}1 0-0')
        assert res[0][1][0][1] == to_utf(['status', 'done'])

        # make sure data is not in the target
        result = self.dbconn.execute(text('select * from persons'))
        assert result.rowcount in [0, -1]

        # make sure data is in redis
        assert self.env.execute_command('hgetall', 'person:1') == to_utf({'first_name':'foo', 'last_name': 'bar', 'age': '20'})

        self.env.execute_command('hset __{person:1} first_name foo last_name bar age 20 # -2')

        res = self.env.execute_command('XREAD BLOCK 200 STREAMS {person:1}2 0-0')
        assert res[0][1][0][1] == to_utf(['status', 'done'])

        # make sure data is deleted from redis
        assert self.env.execute_command('hgetall', 'person:1') == {}

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

connection = PostgresConnection('%s', '%s', '172.17.0.1:5432/%s')
personsConnector = PostgresConnector(connection, 'persons', 'person_id')

personsMappings = {
    'first_name':'first',
    'last_name':'last',
    'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')
RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
""" % (kwargs['dbuser'], kwargs['dbpasswd'], kwargs['db'])
        self.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'psycopg2-binary')

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
        self.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymysql[rsa]')

@pytest.mark.db2
class TestDB2(BaseSQLTest):
    
    def credentials(self):
        r = tox.config.parseconfig(open("tox.ini").read())
        docker = r._docker_container_configs["db2"]["environment"]
        dbuser = docker["DB2INSTANCE"]
        dbpasswd = docker["DB2INST1_PASSWORD"]
        db = docker["DBNAME"]
        
        return {"dbuser": dbuser,
                "dbpasswd": dbpasswd,
                "db": db}
        
    def connection(self, **kwargs):
        
        con = f"db2://{kwargs['dbuser']}:{kwargs['dbpasswd']}@172.17.0.1:50000/{kwargs['db']}"
        return con
    
    def run_install_script(self, pkg, **kwargs):
        script = """
from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import DB2Connector, DB2Connection

connection = DB2Connection('%s', '%s', '172.17.0.1:50000/%s')
personsConnector = DB2Connector(connection, 'persons', 'person_id')

personsMappings = {
    'first_name':'first',
    'last_name':'last',
    'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')
RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
""" % (kwargs['dbuser'], kwargs['dbpasswd'], kwargs['db'])
        self.env.execute_command('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'ibm-db-sa')