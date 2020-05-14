from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import SQLiteConnector, SQLiteConnection

'''
Create MySQL connection object
'''
connection = SQLiteConnection('/home/meir/mydatabase.db')

'''
Create MySQL persons connector
persons - MySQL table to put the data
person_id - primary key
'''
personsConnector = SQLiteConnector(connection, 'persons', 'person_id')

personsMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')
