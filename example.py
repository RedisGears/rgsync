from WriteBehind import RGWriteBehind
from WriteBehind.Connectors import MySqlConnector, MySqlConnection

'''
Create MySql connection object
'''
mySqlConnection = MySqlConnection('demouser', 'Password123!', 'localhost:3306/test')

'''
Create mysql person connector
person1 - mysql table to put the data
id - primary key
'''
mySqlPersonConnector = MySqlConnector(mySqlConnection, 'person1', 'id')

personMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB, keysPrefix='person2', mappings=personMappings, connector=mySqlPersonConnector, name='PersonWriteBehind', version='99.99.99')

'''
Create mysql car connector
car - mysql table to put the data
id - primary key
'''
mySqlCarConnector = MySqlConnector(mySqlConnection, 'car', 'id')

carMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carMappings, connector=mySqlCarConnector, name='CarsWriteBehind', version='99.99.99')