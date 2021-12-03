from redisgears import executeCommand as execute
from rgsync.common import *
import json
import uuid

ackExpireSeconds = 3600

def SafeDeleteKey(key):
    '''
    Deleting a key by first renaming it so we will not trigger another execution
    If key does not exists we will get an execution and ignore it
    '''
    try:
        newKey = '__{%s}__' % key
        execute('RENAME', key, newKey)
        execute('DEL', newKey)
    except Exception:
        pass

def ValidateHash(r):
    key = r['key']
    value = r['value']

    if value == None:
        # key without value consider delete
        value = {OP_KEY : OPERATION_DEL_REPLICATE}
        r['value'] = value
    else:
        # make sure its a hash
        if not (isinstance(r['value'], dict)) :
            msg = 'Got a none hash value, key="%s" value="%s"' % (str(r['key']), str(r['value'] if 'value' in r.keys() else 'None'))
            WriteBehindLog(msg)
            raise Exception(msg)
        if OP_KEY not in value.keys():
            value[OP_KEY] = defaultOperation
        else:
            # we need to delete the operation key for the hash
            execute('hdel', key, OP_KEY)

    op = value[OP_KEY]
    if len(op) == 0:
        msg = 'Got no operation'
        WriteBehindLog(msg)
        raise Exception(msg)

    operation = op[0]

    if operation not in OPERATIONS:
        msg = 'Got unknown operations "%s"' % operation
        WriteBehindLog(msg)
        raise Exception(msg)

    # lets extrac uuid to ack on
    uuid = op[1:]
    value[UUID_KEY] = uuid if uuid != '' else None
    value[OP_KEY] = operation

    r['value'] = value

    return True

def ValidateJSONHash(r):
    key = r['key']
    exists = execute("EXISTS", key)
    if exists == 1:
        r['value'] = {'sync_data': execute("JSON.GET", key)}
        if r['value'] == None:
            r['value'] = {OP_KEY : OPERATION_DEL_REPLICATE}
        r['value'][OP_KEY] = defaultOperation
    else:
        r['value'] = {OP_KEY : OPERATION_DEL_REPLICATE}
    value = r['value']

    operation = value[OP_KEY][0]

    if operation not in OPERATIONS:
        msg = 'Got unknown operations "%s"' % operation
        WriteBehindLog(msg)
        raise Exception(msg)

    # lets extrac uuid to ack on
    uuid = value[OP_KEY][1:]
    value[UUID_KEY] = uuid if uuid != '' else None
    value[OP_KEY] = operation
    r['value'] = value

    return r

def DeleteHashIfNeeded(r):
    key = r['key']
    operation = r['value'][OP_KEY]
    if operation == OPERATION_DEL_REPLICATE:
        SafeDeleteKey(key)

def ShouldProcessHash(r):
    key = r['key']
    value = r['value']
    uuid = value[UUID_KEY]
    operation = value[OP_KEY]
    res = True

    if operation == OPERATION_DEL_NOREPLICATE:
        # we need to just delete the key but delete it directly will cause
        # key unwanted key space notification so we need to rename it first
        SafeDeleteKey(key)
        res = False

    if operation == OPERATION_UPDATE_NOREPLICATE:
        res = False

    if not res and uuid != '':
        # no replication to connector is needed but ack is require
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
        data.append([self.connector.PrimaryKey(), r['key'].split(':')[1]])
        if 'value' in r.keys():
            value = r['value']
            uuid = value.pop(UUID_KEY, None)
            op = value[OP_KEY]
            data.append([OP_KEY, op])
            keys = value.keys()
            if uuid is not None:
                data.append([UUID_KEY, uuid])
            if op == OPERATION_UPDATE_REPLICATE:
                for kInHash, kInDB in self.mappings.items():
                    if kInHash.startswith('_'):
                        continue
                    if kInHash not in keys:
                        msg = 'AddToStream: Could not find %s in hash %s' % (kInHash, r['key'])
                        WriteBehindLog(msg)
                        raise Exception(msg)
                    data.append([kInDB, value[kInHash]])
        execute('xadd', self.GetStreamName(self.connector.TableName()), '*', *sum(data, []))
    return func

def CreateWriteDataFunction(connector, dataKey=None):
    def func(data):
        idsToAck = []
        for d in data:
            originalKey = d['value'].pop(ORIGINAL_KEY, None)
            uuid = d['value'].pop(UUID_KEY, None)
            if uuid is not None and uuid != '':
                idsToAck.append('{%s}%s' % (originalKey, uuid))

        # specifically, to not updating all the old WriteData calls
        # due to JSON
        if dataKey is None:
            connector.WriteData(data)
        else:
            connector.WriteData(data, dataKey)

        for idToAck in idsToAck:
            execute('XADD', idToAck, '*', 'status', 'done')
            execute('EXPIRE', idToAck, ackExpireSeconds)

    return func

class RGWriteBase():
    def __init__(self, mappings, connector, name, version=None):
        UnregisterOldVersions(name, version)

        self.connector = connector
        self.mappings = mappings

        try:
            self.connector.PrepereQueries(self.mappings)
        except Exception as e:
            # cases like mongo, that don't implement this, silence the warning
            if "object has no attribute 'PrepereQueries'" in str(e):
                return
            WriteBehindLog('Skip calling PrepereQueries of connector, err="%s"' % str(e))

def DeleteKeyIfNeeded(r):
    if r['value'][OP_KEY] == OPERATION_DEL_REPLICATE:
        # we need to just delete the key but delete it directly will cause
        # key unwanted key space notification so we need to rename it first
        SafeDeleteKey(r['key'])

def PrepareRecord(r):
    key = r['key']
    value = r['value']

    realKey = key.split('{')[1].split('}')[0]

    realVal = execute('hgetall', realKey)
    realVal = {realVal[i]:realVal[i + 1] for i in range(0, len(realVal), 2)}

    realVal.update(value)

    # delete temporary key
    execute('del', key)

    return {'key': realKey, 'value': realVal}

def TryWriteToTarget(self):
    func = CreateWriteDataFunction(self.connector)
    def f(r):
        key = r['key']
        value = r['value']
        keys = value.keys()
        uuid = value.pop(UUID_KEY, None)
        idToAck = '{%s}%s' % (r['key'], uuid)
        try:
            operation = value[OP_KEY]
            mappedValue = {}
            mappedValue[ORIGINAL_KEY] = key
            mappedValue[self.connector.PrimaryKey()] = key.split(':')[1]
            mappedValue[UUID_KEY] = uuid
            mappedValue[OP_KEY] = operation
            if operation == OPERATION_UPDATE_REPLICATE:
                for kInHash, kInDB in self.mappings.items():
                    if kInHash.startswith('_'):
                        continue
                    if kInHash not in keys:
                        msg = 'Could not find %s in hash %s' % (kInHash, r['key'])
                        WriteBehindLog(msg)
                        raise Exception(msg)
                    mappedValue[kInDB] = value[kInHash]
            func([{'value':mappedValue}])
        except Exception as e:
            WriteBehindLog("Failed writing data to the database, error='%s'" % str(e))
            # lets update the ack stream to failure
            if uuid is not None and uuid != '':
                execute('XADD', idToAck, '*', 'status', 'failed', 'error', str(e))
                execute('EXPIRE', idToAck, ackExpireSeconds)
            return False
        return True
    return f

def UpdateHash(r):
    key = r['key']
    value = r['value']
    operation = value.pop(OP_KEY, None)
    uuid_key = value.pop(UUID_KEY, None)
    if operation == OPERATION_DEL_REPLICATE or operation == OPERATION_DEL_NOREPLICATE:
        SafeDeleteKey(key)
    elif operation == OPERATION_UPDATE_REPLICATE or OPERATION_UPDATE_NOREPLICATE:
        # we need to write to temp key and then rename so we will not
        # trigger another execution
        tempKeyName = 'temp-{%s}' % key
        elemets = []
        for k,v in value.items():
            elemets.append(k)
            elemets.append(v)
        execute('hset', tempKeyName, *elemets)
        execute('rename', tempKeyName, key)
    else:
        msg = "Unknown operation"
        WriteBehindLog(msg)
        raise Exception(msg)

def WriteNoReplicate(r):
    if ShouldProcessHash(r):
        # return true means hash should be replicate and we need to
        # continue processing it
        return True
    # No need to replicate hash, just write it correctly to redis
    operation = r['value'][OP_KEY]
    if operation == OPERATION_UPDATE_NOREPLICATE:
        UpdateHash(r)
    elif operation == OPERATION_DEL_NOREPLICATE:
        # OPERATION_DEL_NOREPLICATE was handled by ShouldProcessHash function
        pass
    else:
        msg = "Unknown operation"
        WriteBehindLog(msg)
        raise Exception(msg)
    return False

class RGWriteBehind(RGWriteBase):
    def __init__(self, GB, keysPrefix, mappings, connector, name, version=None,
                 onFailedRetryInterval=5, batch=100, duration=100, transform=lambda r: r, eventTypes=['hset', 'hmset', 'del', 'change']):
        '''
        Register a write behind execution to redis gears

        GB - The Gears builder object

        keysPrefix - Prefix on keys to register on

        mappings - a dictionary in the following format
            {
                'name-on-redis-hash1':'name-on-connector-table1',
                'name-on-redis-hash2':'name-on-connector-table2',
                .
                .
                .
            }

        connector - a connector object that implements the following methods
            1. TableName() - returns the name of the table to write the data to
            2. PrimaryKey() - returns the name of the public key of the relevant table
            3. PrepereQueries(mappings) - will be called at start to allow the connector to
                prepare the queries. This function is not mandatory and will be called only
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
                connector to achieve exactly once property. The idea is to write the
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

        batch - the batch size on which data will be writen to target

        duration - interval in ms in which data will be writen to target even if batch size did not reached

        onFailedRetryInterval - Interval on which to performe retry on failure.

        transform - A function that accepts as input a redis record and returns a hash

        eventTypes - The events for which to trigger
        '''
        UUID = str(uuid.uuid4())
        self.GetStreamName = CreateGetStreamNameCallback(UUID)

        RGWriteBase.__init__(self, mappings, connector, name, version)

        ## create the execution to write each changed key to stream
        descJson = {
            'name':'%s.KeysReader' % name,
            'version':version,
            'desc':'add each changed key with prefix %s:* to Stream' % keysPrefix,
        }
        GB('KeysReader', desc=json.dumps(descJson)).\
        map(transform).\
        filter(ValidateHash).\
        filter(ShouldProcessHash).\
        foreach(DeleteHashIfNeeded).\
        foreach(CreateAddToStreamFunction(self)).\
        register(mode='sync', prefix='%s:*' % keysPrefix, eventTypes=eventTypes, convertToStr=False)

        ## create the execution to write each key from stream to DB
        descJson = {
            'name':'%s.StreamReader' % name,
            'version':version,
            'desc':'read from stream and write to DB table %s' % self.connector.TableName(),
        }
        GB('StreamReader', desc=json.dumps(descJson)).\
        aggregate([], lambda a, r: a + [r], lambda a, r: a + r).\
        foreach(CreateWriteDataFunction(self.connector)).\
        count().\
        register(prefix='_%s-stream-%s-*' % (self.connector.TableName(), UUID),
                 mode="async_local",
                 batch=batch,
                 duration=duration,
                 onFailedPolicy="retry",
                 onFailedRetryInterval=onFailedRetryInterval,
                 convertToStr=False)

class RGWriteThrough(RGWriteBase):
    def __init__(self, GB, keysPrefix, mappings, connector, name, version=None):
        RGWriteBase.__init__(self, mappings, connector, name, version)

        ## create the execution to write each changed key to database
        descJson = {
            'name':'%s.KeysReader' % name,
            'version':version,
            'desc':'write each changed key directly to databse',
        }
        GB('KeysReader', desc=json.dumps(descJson)).\
        map(PrepareRecord).\
        filter(ValidateHash).\
        filter(WriteNoReplicate).\
        filter(TryWriteToTarget(self)).\
        foreach(UpdateHash).\
        register(mode='sync', prefix='%s*' % keysPrefix, eventTypes=['hset', 'hmset'], convertToStr=False)


GEARSDATAKEY = "redisgears"
class RGJSONWriteBehind(RGWriteBase):
    # JSONWrite Behind
    # The big deal is that:
    # 1. It calls ValidateJSONHash instead of ValidateHash
    # 2. The init requires a data key, in order to go through the sub map and update
    #    within the JSON document.
    def __init__(self, GB, keysPrefix, connector, name, version=None,
                 onFailedRetryInterval=5, batch=100, duration=100,
                 eventTypes=['json.set', 'json.del',
                             'json.strappend', 'json.arrinsert', 'json.arrappend',
                             'json.arrtrim', 'json.arrpop', 'change', 'del'],
                 dataKey=GEARSDATAKEY):

        mappings = {'sync_data': dataKey}
        UUID = str(uuid.uuid4())
        self.GetStreamName = CreateGetStreamNameCallback(UUID)

        RGWriteBase.__init__(self, mappings, connector, name, version)

        # ## create the execution to write each changed key to stream
        descJson = {
            'name':'%s.KeysReader' % name,
            'version':version,
            'desc':'add each changed key with prefix %s:* to Stream' % keysPrefix,
        }

        GB('KeysReader', desc=json.dumps(descJson)).\
        filter(ValidateJSONHash).\
        filter(ShouldProcessHash).\
        foreach(DeleteHashIfNeeded).\
        foreach(CreateAddToStreamFunction(self)).\
        register(mode='sync', prefix='%s:*' % keysPrefix, eventTypes=eventTypes)


        # ## create the execution to write each key from stream to DB
        descJson = {
            'name':'%s.StreamReader' % name,
            'version':version,
            'desc':'read from stream and write to DB table %s' % self.connector.TableName(),
        }
        GB('StreamReader', desc=json.dumps(descJson)).\
        aggregate([], lambda a, r: a + [r], lambda a, r: a + r).\
        foreach(CreateWriteDataFunction(self.connector, dataKey)).\
        count().\
        register(prefix='_%s-stream-%s-*' % (self.connector.TableName(), UUID),
                 mode="async_local",
                 batch=batch,
                 duration=duration,
                 onFailedPolicy="retry",
                 onFailedRetryInterval=onFailedRetryInterval)

class RGJSONWriteThrough(RGWriteBase):
    def __init__(self, GB, keysPrefix, connector, name, version=None, dataKey=GEARSDATAKEY):
        mappings = {'sync_data': dataKey}
        RGWriteBase.__init__(self, mappings, connector, name, version)

        ## create the execution to write each changed key to database
        descJson = {
            'name':'%s.KeysReader' % name,
            'version':version,
            'desc':'write each changed key directly to databse',
        }
        GB('KeysReader', desc=json.dumps(descJson)).\
        map(PrepareRecord).\
        filter(ValidateJSONHash).\
        filter(WriteNoReplicate).\
        filter(TryWriteToTarget(self)).\
        foreach(UpdateHash).\
        register(mode='sync', prefix='%s*' % keysPrefix,
                 eventTypes=['json.set', 'json.del',
                             'json.strappend', 'json.arrinsert', 'json.arrappend',
                             'json.arrtrim', 'json.arrpop', 'change', 'del'])
