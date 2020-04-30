from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import MySqlConnector, MySqlConnection

'''
Create MySQL connection object
All the arguments to the connection can alse be callbacks which will be read each time 
a reconnect attemp is performed. Example:
Read from RedisGears configuration using configGet (https://oss.redislabs.com/redisgears/master/runtime.html#configget) function

def User():
	return configGet('MySqlUser')

def Password():
	return configGet('MySqlPassword')

def DB():
	return configGet('MySqlDB')

connection = MySqlConnection(User, Password, DB)

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

