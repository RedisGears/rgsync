# Setup DB2

# Requirements

Note, running the db2 recipe, requires some local libraries on your running redis instance - due to the requirements of the *ibm-db-sa* library, used for communicating with db2.  Install the equivalent of *libxml2* (libxml2, libxml2-dev, libxml2-devel) on your redis instance, in order to support this recipe.

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
