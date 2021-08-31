# Set up MySql DB

## Setup Mongo docekr
```bash
docker run -p 27017:27017 --name mongo -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=adminpasswd -e MONGO_INITDB_DATABASE=admin
```

# Running the recipe
Assuming you have RedisGears up and running (see [Quick Start](https://oss.redislabs.com/redisgears/quickstart.html)). Please use <a href="https://github.com/RedisGears/gears-cli">gears-cli</a> to send a RedisGears Write-Behind and/or Write-Through recipe for execution. For example, run the sample [MongoDB](example.py) recipe (contains the mapping of MongoDB tables with Redis Hashes and RedisGears registrations) and install its dependencies with the following command:

```bash
gears-cli run --host <host> --port <port> --password <password> example.py --requirements requirements.txt
```

# Test
Using redis-cli perform:
```bash
redis-cli
> hset person:1 first_name foo last_name bar age 20
```

Make sure data reached mongo server - in the mongo cli:
```
mongo -u admin -p adminpass
use rgsync
db.persons.find()
```
