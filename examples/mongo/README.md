# Set up Mongo

Unlike other recipes, this recipe requires a valid redis-server with RedisJSON.

## Setting up a Mongo docker
```bash
docker run -p 27017:27017 --name mongo -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=adminpasswd -e MONGO_INITDB_DATABASE=admin
```

## How this works

A connection is made to mongo, by the redis server, running redisgears.  A JSON mapping is created (see below), so that we can update sub-sections of the JSON document.

The recipe below will write data to a collection called *persons* on the mongo server.  All data stored in *persons* will be part of a json document containing a standard id, and a json document containing the key *gears* at the top level. This json document will contain the data migrated from Redis to Mongo.  

Let's assume the Redis JSON data contains the following: ```{'hello': 'world'}```. In that case the data would be replicated to mongo, appearing as below. Note that Mongo will be adding an _id field for its entry. The *person_id* below, comes from the Redis document, under the assumption that this data was stored in the key *person:1* in Redis.

```
{'_id': ObjectId('617953191b814c4c150bddd4'), 
  'person_id': 1, 
  'gears': {'hello': 'world'}
]

```

The field **dataKey** can have its value replaced with any string, *gears* is only an example.

## Examples

### Gears Recipe for a single write behind

This example replicates all data written to Redis whose key is named *person:<something>*, to the mongo collection named *persons*. The collection name is specified in the instantiation of the MongoConnector below.

```
from rgsync import RGJSONWriteBehind, RGJSONWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

connection = MongoConnection('admin', 'admin', '172.17.0.1:27017/admin')
db = 'yourmongodbname'

jConnector = MongoConnector(connection, db, 'persons', 'person_id')

dataKey = 'gears'

RGJSONWriteBehind(GB,  keysPrefix='person',
              connector=jConnector, name='PersonsWriteBehind',
              version='99.99.99', dataKey=dataKey)

RGJSONWriteThrough(GB, keysPrefix='__', connector=jConnector,
                   name='JSONWriteThrough', version='99.99.99',
                   dataKey=dataKey)
```

### Gears recipe writing to multiple collections

This example recipe builds on the previous case,  and introduces as second replication recipe. In our example, anything stored in Redis under the key *person:<some key>* (eg: person:1, person:15) will be replicated to the *persons* collection in Mongo. Anything written to Redis, and stored under the key  *thing:<some other key>* (eg: thing:42, thing:450) will be replicated to the *secondthings* collection in Mongo.

```
from rgsync import RGJSONWriteBehind, RGJSONWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

connection = MongoConnection('admin', 'admin', '172.17.0.1:27017/admin')
db = 'yourmongodbname'

jConnector = MongoConnector(connection, db, 'persons', 'person_id')

dataKey = 'gears'

RGJSONWriteBehind(GB,  keysPrefix='person',
              connector=jConnector, name='PersonsWriteBehind',
              version='99.99.99', dataKey=dataKey)

RGJSONWriteThrough(GB, keysPrefix='__', connector=jConnector,
                   name='JSONWriteThrough', version='99.99.99',
                   dataKey=dataKey)

secondConnector = MongoConnector(connection, db, 'secondthings', 'thing_id')
RGJSONWriteBehind(GB,  keysPrefix='thing',
              connector=secondConnector, name='SecondThingWriteBehind',
              version='99.99.99', dataKey=dataKey)

RGJSONWriteThrough(GB, keysPrefix='__', connector=secondConnector,
                   name='SecondJSONWriteThrough', version='99.99.99', dataKey=dataKey)
```

### Data storage examples

Data is set in redis using the various json commands from [redisjson](https://redisjson.io). In all cases, initial writes, and updates rely on the same underlying mechanism.

**Storing data**

```
json.set person:1 . '{"hello": "world"}'
```

**Storing data, then adding more fields**

```
json.set person:1 . '{"hello": "world", "my": ["list", "has", "things"]}'
json.set person:1 . '{"someother": "fieldtoadd"}'
```

**Storing data, then updating**

```
json.set person:1 . '{"hello": "world", "my": ["list", "has", "things"]}'
json.set person:1 . '{"hello": "there!"}'
```

**Storing data, then deleting**

```
json.set person:1 . '{"hello": "world"}'
json.del person:1
```
