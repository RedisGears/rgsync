from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import RedisConnector, RedisConnection, RedisClusterConnection

'''
Create Redis Connection
'''
r_conn = RedisConnection(host='127.0.0.1', port=9001)


'''
Create Redis Connector
'''

key_connector = RedisConnector(connection=r_conn, newPrefix='key', exactlyOnceTableName=None)
key_mappings = {
		'bin1' : 'bin1',
		'bin2' : 'bin2',
		'bin3' : 'bin3',
		'bin4' : 'bin4',
		'bin5' : 'bin5'
	}
RGWriteBehind(GB, keysPrefix='key', mappings=key_mappings, connector=key_connector, name='keyWriteBehind', version='99.99.99', onFailedRetryInterval=60)


