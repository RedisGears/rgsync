from redisgears import executeCommand as execute
from WriteBehind.common import WriteBehindLog, WriteBehindDebug, GetStreamName, ORIGINAL_KEY, UUID_KEY
import json

OPERATION_DEL_REPLICATE = '~'
OPERATION_DEL_NOREPLICATE = '-'
OPERATION_UPDATE_REPLICATE = '='
OPERATION_UPDATE_NOREPLICATE = '+'
OPERATIONS = [OPERATION_DEL_REPLICATE, OPERATION_DEL_NOREPLICATE, OPERATION_UPDATE_REPLICATE, OPERATION_UPDATE_NOREPLICATE]
defaultOperation = OPERATION_UPDATE_REPLICATE

def ShouldProcessHash(r):
    hasValue = 'value' in r.keys()
    operation = defaultOperation
    uuid = ''

    if not hasValue:
        # delete command, use the ~ (delete) operation
        operation = OPERATION_DEL_REPLICATE
    else:
        # make sure its a hash
        if not (isinstance(r['value'], dict)) :
            msg = 'Got a none hash value, key="%s" value="%s"' % (str(r['key']), str(r['value'] if 'value' in r.keys() else 'None'))
            WriteBehindLog(msg)
            raise Exception(msg)


    key = r['key']

    if hasValue:
        value = r['value']
        if '#' in value.keys():
            opVal = value['#']
            if len(opVal) == 0:
                msg = 'Got no operation'
                WriteBehindLog(msg)
                raise Exception(msg)
            operation = value['#'][0]
            if operation not in OPERATIONS:
                msg = 'Got unknown operations "%s"' % operation
                WriteBehindLog(msg)
                raise Exception(msg)
            uuid = value['#'][1:]
            if uuid != '':
                value[UUID_KEY] = uuid
            # delete the # field, we already got the information we need
            value.pop('#', None)
            execute('hdel', key, '#')

    res = True

    if operation == OPERATION_DEL_NOREPLICATE:
        # we need to just delete the key but delete it directly will cause
        # key unwanted key space notification so we need to rename it first
        newKey = '__{%s}__' % key
        execute('RENAME', key, newKey)
        execute('DEL', newKey)
        res = False

    if operation == OPERATION_UPDATE_NOREPLICATE:
        res = False

    if not res and uuid != '':
        # no replication to backend is needed but ack is require
        idToAck = '{%s}%s' % (key, uuid)
        execute('XADD', idToAck, '*', 'status', 'done')
        execute('EXPIRE', idToAck, ackExpireSeconds)

    return res

def RegistrationArrToDict(registration, depth):
    if depth >= 2:
        return registration
    if type(registration) is not list:
        return registration
    d = {}
    for i in range(0, len(registration), 2):
        d[registration[i]] = RegistrationArrToDict(registration[i + 1], depth + 1)
    return d

def CompareVersions(v1, v2):
    # None version is less then all version
    if v1 is None:
        return -1
    if v2 is None:
        return 1

    if v1 == '99.99.99':
        return 1
    if v2 == '99.99.99':
        return -1

    v1_major, v1_minor, v1_patch = v1.split('.')
    v2_major, v2_minor, v2_patch = v2.split('.')

    if int(v1_major) > int(v2_major):
        return 1
    elif int(v1_major) < int(v2_major):
        return -1

    if int(v1_minor) > int(v2_minor):
        return 1
    elif int(v1_minor) < int(v2_minor):
        return -1

    if int(v1_patch) > int(v2_patch):
        return 1
    elif int(v1_patch) < int(v2_patch):
        return -1

    return 0

def UnregisterOldVersions(name, version):
    WriteBehindLog('Unregistering old versions of %s' % name)
    registrations = execute('rg.dumpregistrations')
    for registration in registrations:
        registrationDict = RegistrationArrToDict(registration, 0)
        descStr = registrationDict['desc']
        try:
            desc = json.loads(descStr)
        except Exception as e:
            continue
        if 'name' in desc.keys() and name in desc['name']:
            WriteBehindLog('Version auto upgrade is not atomic, make sure to use it when there is not traffic to the database (otherwise you might lose events).', logLevel='warning')
            if 'version' not in desc.keys():
                execute('rg.unregister', registrationDict['id'])
                WriteBehindLog('Unregistered %s' % registrationDict['id'])
                continue
            v = desc['version']
            if CompareVersions(version, v) > 0:
                execute('rg.unregister', registrationDict['id'])
                WriteBehindLog('Unregistered %s' % registrationDict['id'])
            else:
                raise Exception('Found a version which is greater or equals current version, aborting.')
    WriteBehindLog('Unregistered old versions')

def CreateAddToStreamFunction(self):
    def func(r):
        data = []
        data.append([ORIGINAL_KEY, r['key']])
        data.append([self.backend.PrimaryKey(), r['key'].split(':')[1]])
        if 'value' in r.keys():
            keys = r['value'].keys()
            if UUID_KEY in keys:
                data.append([UUID_KEY, r['value'][UUID_KEY]])
            for kInHash, kInDB in self.mappings.items():
                if kInHash.startswith('_'):
                    continue
                if kInHash not in keys:
                    msg = 'Could not find %s in hash %s' % (kInHash, r['key'])
                    WriteBehindLog(msg)
                    raise Exception(msg)
                data.append([kInDB, r['value'][kInHash]])
        execute('xadd', GetStreamName(self.backend.TableName()), '*', *sum(data, []))
    return func

def CreateWriteDataFunction(backend):
    def func(data):
        idsToAck = []
        for d in data:
            originalKey = d.pop(ORIGINAL_KEY, None)
            uuid = d.pop(UUID_KEY, None)
            if uuid is not None:
                idsToAck.append('{%s}%s' % (originalKey, uuid))

        backend.WriteData(data)

        for idToAck in idsToAck:
            execute('XADD', idToAck, '*', 'status', 'done')
            execute('EXPIRE', idToAck, 3600)

    return func

class RGWriteBehind():
    def __init__(self, GB, keysPrefix, mappings, backend, 
                 name='WriteBehind', version=None, onFailedRetryInterval=5):
        '''
        Register a write behind execution to redis gears

        GB - The Gears builder object
        
        keysPrefix - Prefix on keys to register on
        
        mappings - a dictionary in the following format
            {
                'name-on-redis-hash1':'name-on-backend-table1',
                'name-on-redis-hash2':'name-on-backend-table2',
                .
                .
                .
            }
    
        backend - a backend object that implements the following methods
            1. TableName() - returns the name of the table to write the data to
            2. PrimaryKey() - returns the name of the public key of the relevant table
            3. PrepereQueries(mappings) - will be called at start to allow the backend to
                prepere the quiries. This function is not mandatory and will be called only
                if exists.
            4. WriteData(data) - 
                data is a list of dictionaries of the following format

                    {
                        'streamId':'value'
                        'name-of-column':'value-of-column',
                        'name-of-column':'value-of-column',
                        .
                        .

                    }

                The streamId is a unique id of the dictionary and can be used by the 
                backend to achieve exactly once property. The idea is to write the 
                last streamId of a batch into another table. When new connection
                established, this streamId should be read from the database and
                data with lower stream id should be ignored
                The stream id is in a format of '<timestamp>-<increasing counter>' so there
                is a total order between all streamIds

                The WriteData function should write all the entries in the list to the database
                and return. On error it should raise exception.

                This function should ignore keys that starts with '_'

        name - The name of the created registration. This name will be used to find old version
               and remove them.

        version - The version to set to the new created registration. Old versions with the same
               name will be removed. 99.99.99 is greater then any other version (even from itself).

        onFailedRetryInterval - Interval on which to performe retry on failure.
        '''
        
        ## create the execution to write each changed key to stream

        UnregisterOldVersions(name, version)

        self.backend = backend
        self.mappings = mappings

        try:
            self.backend.PrepereQueries(self.mappings)
        except Exception as e:
            WriteBehindLog('Skip calling PrepereQueries of backend, err="%s"' % str(e))


        ## create the execution to write each changed key to stream
        descJson = {
            'name':'%s.KeysReader' % name,
            'version':version,
            'desc':'add each changed key with prefix %s:* to Stream' % keysPrefix,
        }
        GB('KeysReader', desc=json.dumps(descJson)).\
        filter(lambda x: x['key'] != GetStreamName(self.backend.TableName())).\
        filter(ShouldProcessHash).\
        foreach(CreateAddToStreamFunction(self)).\
        register(mode='sync', regex='%s:*' % keysPrefix, eventTypes=['hset', 'hmset', 'del'])

        ## create the execution to write each key from stream to DB
        descJson = {
            'name':'%s.StreamReader' % name,
            'version':version,
            'desc':'read from stream and write to DB table %s' % self.backend.TableName(),
        }
        GB('StreamReader', desc=json.dumps(descJson)).\
        aggregate([], lambda a, r: a + [r], lambda a, r: a + r).\
        foreach(CreateWriteDataFunction(self.backend)).\
        count().\
        register(regex='_%s-stream-*' % self.backend.TableName(),
                 mode="async_local",
                 batch=100,
                 duration=100,
                 onFailedPolicy="retry",
                 onFailedRetryInterval=onFailedRetryInterval)
        
