from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import SnowflakeSqlConnector, SnowflakeSqlConnection

'''
Create Snowflake connection object
The connection object will be translated to snowflake://<user>:<password>@<account>/<db>
'''
connection = SnowflakeSqlConnection('<user>', '<password>', '<account>', '<db>')

'''
Create Snowflake person1 connector
persons - Snowflake table to put the data
id - primary key
'''
personsConnector = SnowflakeSqlConnector(connection, 'person1', 'id')

personsMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')

'''
Create Snowflake car connector
car - Snowflake table to put the data
license - primary key
'''
carsConnector = SnowflakeSqlConnector(connection, 'car', 'license')

carsMappings = {
	'license':'license',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carsMappings, connector=carsConnector, name='CarsWriteBehind', version='99.99.99')
