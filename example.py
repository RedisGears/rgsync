from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import MySqlConnector, MySqlConnection

'''
Create MySQL connection object
All the arguments to the connection can also be callbacks which will be called each time a reconnect attempt is performed. 
Example:
Read from RedisGears configuration using configGet (https://oss.redislabs.com/redisgears/master/runtime.html#configget) function

def User():
	return configGet('MySqlUser')

def Password():
	return configGet('MySqlPassword')

def DB():
	return configGet('MySqlDB')

connection = MySqlConnection(User, Password, DB)

'''
connection = MySqlConnection('root', 'cacafuti', '10.250.16.49:3306/test')

'''
Create MySQL measures connector
measures - MySQL table to put the data
measure_id - primary key
'''
measuresConnector = MySqlConnector(connection, 'measures', 'measure_id')

measuresMappings = {
	'key':'key',
	'value':'value'
}

RGWriteBehind(GB,  keysPrefix='measure', mappings=measuresMappings, connector=measuresConnector, name='MeasuresWriteBehind',  version='99.99.99')