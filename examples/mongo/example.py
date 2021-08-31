from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

'''
Create Mongo connection object
'''
connection = MongoConnection('demouser', 'Password123!', 'localhost:3306/test')

'''
Create Mongo persons connector
'''
personsConnector = MongoConnector(connection, 'persons', 'person_id')

personsMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')