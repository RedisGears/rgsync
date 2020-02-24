from WriteBehind import RGWriteBehind
from WriteBehind.Connectors import CqlConnector, CqlConnection

'''
Create CQL connection object
'''
cqlConnection = CqlConnection('cassandra', 'cassandra', 'localhost', 'test')

'''
Create CQL person connector
persons - CQL table to put the data
person_id - primary key
'''
cqlPersonConnector = CqlConnector(cqlConnection, 'persons', 'person_id')

personMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB, keysPrefix='person', mappings=personMappings, connector=cqlPersonConnector, name='PersonWriteBehind', version='99.99.99')

'''
Create CQL car connector
cars - CQL table to put the data
car_id - primary key
'''
cqlCarConnector = CqlConnector(cqlConnection, 'cars', 'car_id')

carMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carMappings, connector=cqlCarConnector, name='CarsWriteBehind', version='99.99.99')
