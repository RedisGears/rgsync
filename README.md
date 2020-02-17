# WriteBehind
Write Behind Recipe for [RedisGears](https://github.com/RedisGears/RedisGears)
# Demo
![WriteBehind demo](demo/WriteBehindDemo.gif)

# Example
Running this example will write all hash with prefix `person2:<id>` to mysql database table `person1` and all hash with prefix `car:<id>` to mysql database table `car`
```python
from WriteBehind import RGWriteBehind
from WriteBehind.Backends import MySqlBackend

'''
Create mysql person backend
person1 - mysql table to put the data
id - primary key
'''
mySqlPersonBackend = MySqlBackend('demouser', 'Password123!', 'localhost:3306/test', 'person1', 'id')

personMappings = {
	'first_name':'first',
	'last_name':'last',
	'age':'age'
}

RGWriteBehind(GB, keysPrefix='person2', mappings=personMappings, backend=mySqlPersonBackend, name='PersonWriteBehind', version='99.99.99')

'''
Create mysql car backend
car - mysql table to put the data
id - primary key
'''
mySqlCarBackend = MySqlBackend('demouser', 'Password123!', 'localhost:3306/test', 'car', 'id')

carMappings = {
	'id':'id',
	'color':'color'
}

RGWriteBehind(GB, keysPrefix='car', mappings=carMappings, backend=mySqlCarBackend, name='CarsWriteBehind', version='99.99.99')
```
# Run
Use [this](https://github.com/RedisGears/RedisGears/blob/master/recipes/gears.py) script to send the Gear to RedisGears:
```bash
python gears.py --host <host> --port <post> --password <password> example.py REQUIREMENTS git+https://github.com/RedisGears/WriteBehind.git PyMySQL
```
# How Does it Work?
* Key is written to the database and trigger the first Gear registration
* The Gears registration writes the data to Redis stream which trigger the second Gear registration
* The second Gear registration read the data from the Redis stream and write it to the backend

## Why Redis Stream is Required?
The first Gear registration is a sync registration, which means that it triggers on the same thread on which the command was executed (i.e, the main thread, It is possible to trigger an async registration but then redis will return the reply before the data was actually written to somewhere and if the redis will crash before the registration will finish we will lose the event). Writing directly to the backend is slow (on most backends) and will come with performance panelty, so we have a Redis stream that store all the changes and an async execution that reads from the Redis stream and write to the backend in the background.

# Advance Usage
Sometimes you want to delete/add data to redis without replicate it to the backend. It is easy to acheive it by adding the `#` field to the hash with one of the following operations as a value:
* `+` - Add the data without replicating
* `=` - Add the data with replicating (the default behavior)
* `-` - delete the data without replicating
* `~` - delete the data with replicating (the default behavior when using `del` command)

If the `#` field exist the Write Behind recipe will act according to its value and then delete it. So for example, to delete a hash without replicating the delete operation just do:
```
hset person2:1 # -
```

Or if you want to add a hash without replicate it to the backend, just do:
```
hset person2:1 first_name foo last_name bar age 20 # +
```

# Get Acknowledgement
Sometimes you want to get an acknowledge that your data was successfully written to the backend. Write Behind recipe allows you do get this acknowledgement in the following maner:
* Generate a `uuid`
* Add this `uuid` to the value of the `#` field right after the operation (i.e, after `+`/`=`/`-`/`~`, notice that you must specify an operation if you use this feature)
* Do `XREAD BLOCK <timeout> STREAMS {<hash key>}<uuid> 0-0`. After the data is written to the backend the Write Behind recipe will push a data to this stream (`{<hash key>}<uuid>`) with the following field and value : `{'status':'done'}`.
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
To avoid events lost, that will follow with inconsistencies between Redis and the backend, it is highly recommended to use replication. When the primary crash and the secondary is promoted, the secondary will continue from where the primary stopped.

It is also possible to use AOF to make sure we do not lose events.

#Monitor
Use [this](https://github.com/RedisGears/RedisGearsMonitor) to monitor the created registrations