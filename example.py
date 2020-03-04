from WriteBehind import RGWriteBehind, RGWriteThrough
from WriteBehind.Connectors import MySqlConnector, MySqlConnection

'''
Create MySQL connection object
'''
mySqlConnection = MySqlConnection('demouser', 'Password123!', 'localhost:3306/test')

'''
Create MySQL person connector
persons - MySQL table to put the data
person_id - primary key
'''
mySqlPersonConnector = MySqlConnector(mySqlConnection, 'persons', 'person_id')

personMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB, keysPrefix='person', mappings=personMappings, connector=mySqlPersonConnector, name='PersonWriteBehind', version='99.99.99')

RGWriteThrough(GB, keysPrefix='__', mappings=personMappings, connector=mySqlPersonConnector, name='PersonWriteThrough', version='99.99.99')

'''
Create MySQL car connector
cars - MySQL table to put the data
car_id - primary key
'''
mySqlCarConnector = MySqlConnector(mySqlConnection, 'cars', 'car_id')

carMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carMappings, connector=mySqlCarConnector, name='CarsWriteBehind', version='99.99.99')
