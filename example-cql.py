from WriteBehind import RGWriteBehind
from WriteBehind.Connectors import CqlConnector, CqlConnection

'''
Create CQL connection object
'''
connection = CqlConnection('cassandra', 'cassandra', 'cassandra', 'test')

'''
Create CQL person connector
persons - CQL table to put the data
person_id - primary key
'''
personsConnector = CqlConnector(connection, 'persons', 'person_id')

personsMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')

'''
Create CQL cars connector
cars - CQL table to put the data
car_id - primary key
'''
carConnector = CqlConnector(connection, 'cars', 'car_id')

carsMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carsMappings, connector=carsConnector, name='CarsWriteBehind', version='99.99.99')
