# Setup DB2

# Running the recipe
Assuming you have RedisGears up and running (see [Quick Start](https://oss.redislabs.com/redisgears/quickstart.html)). Please use <a href="https://github.com/RedisGears/gears-cli">gears-cli</a> to send a RedisGears Write-Behind and/or Write-Through recipe for execution. For example, run the sample [DB2](example.py) recipe (contains the mapping of DB2 tables with Redis Hashes and RedisGears registrations) and install its dependencies with the following command:

```bash
gears-cli run --host <host> --port <port> --password <password> example.py --requirements requirements.txt
```
e.g.
```bash
> gears-cli run --host localhost --port 14000 example.py --requirements requirements.txt
OK
```

# Test
Using redis-cli perform:
```bash
redis-cli
> hset emp:1 FirstName foo LastName bar
```

Make sure data reached MsSql server:
