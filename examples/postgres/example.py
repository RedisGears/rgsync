from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import PostgresConnector, PostgresConnection

'''
Create Postgres connection object
'''
connection = PostgresConnection('demo', 'Password123!', 'localhost:5432/test')

'''
Create Postgres persons connector
'''
personsConnector = PostgresConnector(connection, 'persons', 'person_id')

personsMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
