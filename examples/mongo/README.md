# Set up Mongo

Unlike other recipes, this recipe requires a valid redis-server with RedisJSON.

## Setting up a Mongo docker
```bash
docker run -p 27017:27017 --name mongo -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=adminpasswd -e MONGO_INITDB_DATABASE=admin
```

## How this works

A connection is made to mongo, by the redis server, running redisgears.  A JSON mapping is created (see below), so that we can update sub-sections of the JSON document.

The recipe below will write data to a collection called *persons* on the mongo server.  All data stored in *persons* will be part of a json document containing a standard id, and a *gears* json document. This json document will contain the data migrated from Redis to Mongo.  Partial updates search for their associated fields within that *gears* object.

```
from rgsync import RGJSONWriteBehind, RGJSONWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

connection = MongoConnection('admin', 'admin', '172.17.0.1:27017/admin')
db = 'yourmongodbname'

jConnector = MongoConnector(connection, db, 'persons', 'person_id')

jMappings = {'redis_data': 'gears'}

RGJSONWriteBehind(GB,  keysPrefix='person', mappings=jMappings,
              connector=jConnector, name='PersonsWriteBehind',
              version='99.99.99', dataKey='gears')

RGJSONWriteThrough(GB, keysPrefix='__', mappings=jMappings, connector=jConnector, name='JSONWriteThrough', version='99.99.99')
```

## Example

Data is set in redis using the various json commands from [redisjson](https://redisjson.io). In all cases, initial writes, and updates rely on the same underlying mechanism.

**Storing data**

```
json.set person:1 . '{"redis_data": {"hello": "world"}}'
```

**Storing data, then adding more fields**

```
json.set person:1 . '{"redis_data": {"hello": "world", "my": ["list", "has", "things"]}}'
json.set person:1 . '{"redis_data": {"someother": "fieldtoadd"}}'
```

**Storing data, then updating**

```
json.set person:1 . '{"redis_data": {"hello": "world", "my": ["list", "has", "things"]}}'
json.set person:1 . '{"redis_data": {"hello": "there!"}}'
```

**Storing data, then deleting**

```
json.set person:1 . '{"redis_data": {"hello": "world"}}'
json.del person:1
```
