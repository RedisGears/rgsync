from WriteBehind import RGWriteBehind, RGWriteThrough
from WriteBehind.Connectors import MySqlConnector, MySqlConnection

'''
Create MySQL connection object
'''
connection = MySqlConnection('demouser', 'Password123!', 'localhost:3306/test')

'''
Create MySQL persons connector
persons - MySQL table to put the data
person_id - primary key
'''
personsConnector = MySqlConnector(connection, 'persons', 'person_id')

personsMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')

RGWriteThrough(GB, keysPrefix='__', mappings=personMappings, connector=mySqlPersonConnector, name='PersonWriteThrough', version='99.99.99')

'''
Create MySQL cars connector
cars - MySQL table to put the data
car_id - primary key
'''
carsConnector = MySqlConnector(connection, 'cars', 'car_id')

carsMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carsMappings, connector=carsConnector, name='CarsWriteBehind', version='99.99.99')
