from WriteBehind import RGWriteBehind
from WriteBehind.Backends import MySqlBackend

mySqlPersonBackend = MySqlBackend('demouser', 'Password123!', 'localhost:3306/test', 'person1', 'id')

personMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB, keysPrefix='person2', mappings=personMappings, backend=mySqlPersonBackend, name='PersonWriteBehind', version='99.99.99')

mySqlCarBackend = MySqlBackend('demouser', 'Password123!', 'localhost:3306/test', 'car', 'id')

carMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carMappings, backend=mySqlCarBackend, name='CarsWriteBehind', version='99.99.99')