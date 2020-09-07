## Running the recipe
Please use <a href="https://github.com/RedisGears/gears-cli">gears-cli</a> to send a RedisGears Write-Behind and/or Write-Through recipe for execution. 
For example, run the sample [redis](example-redis.py) recipe (contains the mapping of primary DB Redis Hashes with secondary DB Redis Hashes and RedisGears registrations) and install its dependencies with the following command:

```bash
gears-cli run --host <host> --port <port> --password <password> example-redis.py --requirements requirements.txt
```

NOTE:	Exactly once property is not valid for Redis cluster, because Redis cluster do not support transaction over multiple shards.

