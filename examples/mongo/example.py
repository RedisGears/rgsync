from rgsync import RGJSONWriteBehind, RGJSONWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection
'''
Create Mongo connection object
'''
connection = MongoConnection('admin', 'admin', '172.17.0.1:27017/admin')


'''
Create Mongo persons connector
'''
jConnector = MongoConnector(connection, db, 'persons', 'person_id')
jMappings = {'redis_data': 'gears'}

RGJSONWriteBehind(GB,  keysPrefix='person', mappings=jMappings,
              connector=jConnector, name='PersonsWriteBehind',
              version='99.99.99', dataKey='gears')

RGJSONWriteThrough(GB, keysPrefix='__', mappings=jMappings, connector=jConnector, name='JSONWriteThrough', version='99.99.99')

