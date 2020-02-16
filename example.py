from WriteBehind import RGWriteBehind
from WriteBehind.Backends import MySqlBackend

mySqlBackend = MySqlBackend('demouser', 'Password123!', 'localhost:3306/test', 'person1', 'id')

mappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB, keysPrefix='person2', mappings=mappings, backend=mySqlBackend, name='PersonWriteBehind', version='99.99.99')