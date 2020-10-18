# Set up Redis Server
To setup a Redis server to replicate data to, start another Redis server on different port (assuming you have Redis installed on the machine)
```bash
redis-server --port 9001
```

## Running the recipe
Please use <a href="https://github.com/RedisGears/gears-cli">gears-cli</a> to send a RedisGears Write-Behind and/or Write-Through recipe for execution. 
For example, run the sample [redis](example-redis-standalone.py) recipe (contains the mapping of primary DB Redis Hashes with secondary DB Redis Hashes and RedisGears registrations) and install its dependencies with the following command:

```bash
gears-cli run --host <host> --port <port> --password <password> example-redis-standalone.py --requirements requirements.txt
```

NOTE:	Exactly once property is not valid for Redis cluster, because Redis cluster do not support transaction over multiple shards.

# Test
Using redis-cli perform:
```bash
redis-cli
127.0.0.1:6379> hset key:1 bin1 1 bin2 2 bin3 3 bin4 4 bin5 5
(integer) 5
```

Make sure data reached the second Redis server:
```bash
redis-cli -p 9001
127.0.0.1:9001> hgetall key:1
 1) "bin1"
 2) "1"
 3) "bin2"
 4) "2"
 5) "bin4"
 6) "4"
 7) "bin3"
 8) "3"
 9) "bin5"
10) "5"
```
