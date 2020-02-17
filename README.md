# WriteBehind
Write Behind Recipe for [RedisGears](https://github.com/RedisGears/RedisGears)
# Demo
![WriteBehind demo](demo/WriteBehindDemo.gif)

# Example
Running this example will write all hash with prefix `person:<id>` to mysql database table `person_table` (using `<id>` as a primary key mapped to `person_id`) and all hash with prefix `car:<id>` to mysql database table `car_table`
```python
from WriteBehind import RGWriteBehind
from WriteBehind.Connectors import MySqlConnector, MySqlConnection

'''
Create MySql connection object
'''
mySqlConnection = MySqlConnection('demouser', 'Password123!', 'localhost:3306/test')

'''
Create mysql person connector
person_table - mysql table to put the data
person_id - primary key
'''
mySqlPersonConnector = MySqlConnector(mySqlConnection, 'person_table', 'person_id')

personMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB, keysPrefix='person', mappings=personMappings, connector=mySqlPersonConnector, name='PersonWriteBehind', version='99.99.99')

'''
Create mysql car connector
car_table - mysql table to put the data
car_id - primary key
'''
mySqlCarConnector = MySqlConnector(mySqlConnection, 'car_table', 'car_id')

carMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carMappings, connector=mySqlCarConnector, name='CarsWriteBehind', version='99.99.99')
```
# Run
Use [this](https://github.com/RedisGears/RedisGears/blob/master/recipes/gears.py) script to send the Gear to RedisGears:
```bash
python gears.py --host <host> --port <post> --password <password> example.py REQUIREMENTS git+https://github.com/RedisGears/WriteBehind.git PyMySQL
```
# How Does it Work?
* Key is written to the database and trigger the first Gear registration
* The Gears registration writes the data to Redis stream which trigger the second Gear registration
* The second Gear registration read the data from the Redis stream and write it to the connector

## Why Redis Stream is Required?
The first Gear registration is a sync registration, which means that it triggers on the same thread on which the command was executed (i.e, the main thread, It is possible to trigger an async registration but then redis will return the reply before the data was actually written to somewhere and if the redis will crash before the registration will finish we will lose the event). Writing directly to the connector is slow (on most connectors) and will come with performance panelty, so we have a Redis stream that store all the changes and an async execution that reads from the Redis stream and write to the connector in the background.

# Advance Usage
Sometimes you want to delete/add data to redis without replicate it to the connector. It is easy to acheive it by adding the `#` field to the hash with one of the following operations as a value:
* `+` - Add the data without replicating
* `=` - Add the data with replicating (the default behavior)
* `-` - delete the data without replicating
* `~` - delete the data with replicating (the default behavior when using `del` command)

If the `#` field exist the Write Behind recipe will act according to its value and then delete it. So for example, to delete a hash without replicating the delete operation just do:
```
hset person2:1 # -
```

Or if you want to add a hash without replicate it to the connector, just do:
```
hset person2:1 first_name foo last_name bar age 20 # +
```

# Get Acknowledgement
Sometimes you want to get an acknowledge that your data was successfully written to the connector. Write Behind recipe allows you do get this acknowledgement in the following maner:
* Generate a `uuid`
* Add this `uuid` to the value of the `#` field right after the operation (i.e, after `+`/`=`/`-`/`~`, notice that you must specify an operation if you use this feature)
* Do `XREAD BLOCK <timeout> STREAMS {<hash key>}<uuid> 0-0`. After the data is written to the connector the Write Behind recipe will push a data to this stream (`{<hash key>}<uuid>`) with the following field and value : `{'status':'done'}`.
* It is recommended to delete the stream after getting the acknowledgement though its not a must, the stream are created with an expiration value of one hour.

## Example
```
127.0.0.1:6379> hset person2:1 first_name foo last_name bar age 20 # =6ce0c902-30c2-4ac9-8342-2f04fb359a94
(integer) 1
127.0.0.1:6379> XREAD BLOCK 2000 STREAMS {person2:1}6ce0c902-30c2-4ac9-8342-2f04fb359a94 0-0
1) 1) "{person2:1}6ce0c902-30c2-4ac9-8342-2f04fb359a94"
   2) 1) 1) "1581927201056-0"
         2) 1) "status"
            2) "done"
```

# Recommendations
To avoid events lost, that will follow with inconsistencies between Redis and the connector, it is highly recommended to use replication. When the primary crash and the secondary is promoted, the secondary will continue from where the primary stopped.

It is also possible to use AOF to make sure we do not lose events.

# Monitor
Use [this](https://github.com/RedisGears/RedisGearsMonitor) to monitor the created registrations