from rgsync import RGWriteBehind
from rgsync.Connectors import RedisConnector, RedisConnection, RedisClusterConnection

'''
Create Redis Cluster Connection
'''
cnodes = [{"host": "127.0.0.1", "port": "7001"}, {"host": "127.0.0.1", "port": "7002"}, {"host": "127.0.0.1", "port": "7003"}]
r_conn = RedisClusterConnection(host=None, port=None, cluster_nodes=cnodes)


'''
Create Redis Connector
'''

student_connector = RedisConnector(connection=r_conn, newPrefix='Student', exactlyOnceTableName=None)
student_mappings = {
        'name' : 'Name',
        'age' : 'Age',
        'rollno' : 'RollNo'
        }
RGWriteBehind(GB, keysPrefix='student', mappings=student_mappings, connector=student_connector, name='StudentWriteBehind', version='99.99.99', onFailedRetryInterval=60)




person_connector = RedisConnector(connection=r_conn, newPrefix='Person', exactlyOnceTableName=None)
person_mappings = {
        'first_name' : 'First',
        'last_name' : 'Last',
        'age' : 'Age'
        }
RGWriteBehind(GB, keysPrefix='person', mappings=person_mappings, connector=person_connector, name='PersonWriteBehind', version='99.99.99', onFailedRetryInterval=60)

