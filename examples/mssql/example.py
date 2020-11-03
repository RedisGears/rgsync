from rgsync.Connectors import MsSqlConnector, MsSqlConnection
from rgsync import RGWriteBehind, RGWriteThrough

'''
Create MSSQL connection object
MsSqlConnection('<user>', '<password>', '<db>', '<server>', '<db_port>', '<driver>')
********* Redis OSS users: please use localhost for <server> value *********
'''
connection = MsSqlConnection('sa', 'Redis@123', 'RedisGearsTest', '172.18.0.5', '1433', 'ODBC+Driver+17+for+SQL+Server')

'''
Create MSSQL emp connector
MsSqlConnector(<connection>, '<table_name>', '<primary_key>')
'''
empConnector = MsSqlConnector(connection, 'emp', 'empno')

empMappings = {
        #redis:database
        'FirstName':'fname',
        'LastName':'lname'
}

RGWriteBehind(GB,  keysPrefix='emp', mappings=empMappings, connector=empConnector, name='empWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',  mappings=empMappings, connector=empConnector, name='empWriteThrough', version='99.99.99')
