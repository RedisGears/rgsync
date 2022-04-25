from rgsync.Connectors import DB2Connection, DB2Connector
from rgsync import RGWriteBehind, RGWriteThrough

'''
Create DB2 connection object
'''
connection = DB2Connection('user', 'pass', 'host[:port]/dbname')

'''
Create DB2 emp connector
'''
empConnector = DB2Connector(connection, 'emp', 'empno')

empMappings = {
        'FirstName':'fname',
        'LastName':'lname'
}

RGWriteBehind(GB,  keysPrefix='emp', mappings=empMappings, connector=empConnector, name='empWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',  mappings=empMappings, connector=empConnector, name='empWriteThrough', version='99.99.99')
