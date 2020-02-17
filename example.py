from WriteBehind import RGWriteBehind
from WriteBehind.Backends import MySqlBackend

'''
Create mysql person backend
person1 - mysql table to put the data
id - primary key
'''
mySqlPersonBackend = MySqlBackend('demouser', 'Password123!', 'localhost:3306/test', 'person1', 'id')

personMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB, keysPrefix='person2', mappings=personMappings, backend=mySqlPersonBackend, name='PersonWriteBehind', version='99.99.99')

'''
Create mysql car backend
car - mysql table to put the data
id - primary key
'''
mySqlCarBackend = MySqlBackend('demouser', 'Password123!', 'localhost:3306/test', 'car', 'id')

carMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carMappings, backend=mySqlCarBackend, name='CarsWriteBehind', version='99.99.99')