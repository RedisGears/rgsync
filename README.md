# WriteBehind
Write Behind Recipe for [RedisGears](https://github.com/RedisGears/RedisGears)

## Demo
![WriteBehind demo](demo/WriteBehindDemo.gif)

## Example
The following is a RedisGears recipe that shows how to use the write behind pattern to map data from Redis Hashes to MySQL tables. The recipe maps all Redis Hashes with the prefix `person:<id>` to the MySQL table `persons`, with `<id>` being the a primary key and mapped to the `person_id` column. In a similar fashion, it maps all Hashes with the prefix `car:<id>` to the `cars` table.

```python
from WriteBehind import RGWriteBehind
from WriteBehind.Connectors import MySqlConnector, MySqlConnection

'''
Create MySQL connection object
'''
connection = MySqlConnection('demouser', 'Password123!', 'localhost:3306/test')

'''
Create MySQL persons connector
persons - MySQL table to put the data
person_id - primary key
'''
personConnector = MySqlConnector(mySqlConnection, 'persons', 'person_id')

personsMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB, keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind', version='99.99.99')

'''
Create MySQL car connector
cars - MySQL table to put the data
car_id - primary key
'''
carConnector = MySqlConnector(connection, 'cars', 'car_id')

carsMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='cars', mappings=carsMappings, connector=carsConnector, name='CarsWriteBehind', version='99.99.99')
```

## Running the recipe
You can use [this utility](https://github.com/RedisGears/RedisGears/blob/master/recipes/gears.py) to send a RedisGears recipe for execution. For example, run this repository's [example.py recipe](example.py) and install its dependencies with the following command:

```bash
python gears.py --host <host> --port <post> --password <password> example.py REQUIREMENTS git+https://github.com/RedisGears/WriteBehind.git PyMySQL
```

## Overview of the recipe's operation
The [`RGWriteBehind()` class](WriteBehind/redis_gears_write_behind.py) implements the write behind recipe, that mainly consists of two RedisGears functions and operates as follows:
1. A write operation to a Redis Hash key triggers the execution of a RedisGears function.
1. That RedisGears function reads the data from the Hash and writes into a Redis Stream.
1. Another RedisGears function is executed asynchronously in the background and writes the changes to the target database.

### The motivation for using a Redis Stream
The use of a Redis Stream in the write behind recipe implementation is to ensure the persistence of captured changes, while mitigating the performance penalty associated with shipping them to the target database.

The recipe's first RedisGears function is registered to run synchronously, which means that the function runs in the same main Redis thread in which the command was executed. This mode of execution is needed so changes events are recorded in order and to eliminate the possibility of loosing events in case of failure.

Applying the changes to the target database is usually much slower, effectively excluding the possibility of doing that in the main thread. The second RedisGears function is executed asynchronously on batches and in intervals to do that.

The Redis Stream is the channel through which both of the recipe's parts communicate, where the changes are persisted in order synchronously and are later processed in the background asynchronously.

## Controlling what gets replicated
Sometimes you want to modify the data in Redis without replicating it to the target. For that purpose, the recipe can be customized by adding the special field `#` to your Hash's fields and setting it to one of these values:
* `+` - Adds the data but does not replicate it to the target
* `=` - Adds the data with and replicates it (the default behavior)
* `-` - Deletes the data but does not replicate
* `~` - Deletes the data from Redis and the target (the default behavior when using `del` command)

When the Hash's value contains the `#` field, the recipe will act according to its value and will delete the `#` field from the Hash afterwards. For example, the following shows how to delete a Hash without replicating the delete operation:

```
redis> HSET person:1 # -
```

Alternatively, to add a Hash without having it replicated:
```
redis> HSET person:007 first_name James last_name Bond age 42 # +
```

## At least once and exactly once writes
By default the write behind recipe provides the "at least once" property for writes, meaning that data will be written once to the target, but possibly more than that in cases of failure.

It is possible to have recipe provide "exactly once" delivery semantics by using the Stream's message ID as an increasing ID of the operations. The writer RedisGears function can use that ID and record it in another table in the target to ensure that any given ID is only be written once.

All of the recipe's SQL connectors support this capability. To use it, you need to provide the connector with the name of the "exactly once" table. This table should contains 2 columns, the `id` which represent some unique ID of the writer (used to distinguish between shards for example) and `val` which is the last Stream ID written to the target. The "exactly once" table's name can be specified to the connector in the constructor via the optional `exactlyOnceTableName` variable.

## Getting write acknowledgement
It is possible to use the recipe and get an acknowledgement of successful writes to the target. Follow this steps to do so:
1. For each data-changing operation generate a `uuid`.
2. Add the operation's `uuid` immediately after the value in the special `#` field , that is after the `+`/`=`/`-`/`~` character. Enabling write acknowledgement requires the use of the special `#`.
3. After performing the operation, perform an `XREAD BLOCK <timeout> STREAMS {<hash key>}<uuid> 0-0`. Once the recipe has written to the target, it will create a message in that (`{<hash key>}<uuid>`) Stream that has a single field named 'status' with the value 'done'.
4. For housekeeping purposes it is recommended to delete that Stream after getting the acknowledgement. This is not a a must, however, as these Streams are created with TTL of one hour.

### Acknowledgement example
```
127.0.0.1:6379> hset person:007 first_name James last_name Bond age 42 # =6ce0c902-30c2-4ac9-8342-2f04fb359a94
(integer) 1
127.0.0.1:6379> XREAD BLOCK 2000 STREAMS {person:1}6ce0c902-30c2-4ac9-8342-2f04fb359a94 0-0
1) 1) "{person:1}6ce0c902-30c2-4ac9-8342-2f04fb359a94"
   2) 1) 1) "1581927201056-0"
         2) 1) "status"
            2) "done"
```

## Data persistence and availability
To avoid data loss in Redis and the resulting inconsistencies with the target databases, it is recommended to employ and use this recipe only with a highly-available Redis environment. In such environments, the failure of a master node will cause the replica that replaced it to continue the recipe's execution from the point it was stopped.

Furthermore, Redis' AOF should be used alongside replication to protect against data loss during system-wide failures.

## Monitoring the RedisGears function registrations
Use [this](https://github.com/RedisGears/RedisGearsMonitor) to monitor RedisGear's function registrations.