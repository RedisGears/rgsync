# Set up Postgres DB

## Setup Postgres docker
```bash
docker run -p 5432:5432 --name some-postgres -e POSTGRES_ROOT_PASSWORD=my-secret-pw -d postgres:latest
```

## Create Persons table

See [Postgres setup scripts](../sbin/setup-postgres).

# Running the recipe
Assuming you have RedisGears up and running (see [Quick Start](https://oss.redislabs.com/redisgears/quickstart.html)). Please use <a href="https://github.com/RedisGears/gears-cli">gears-cli</a> to send a RedisGears Write-Behind and/or Write-Through recipe for execution. For example, run the sample [Postgres](example.py) recipe (contains the mapping of Postgres tables with Redis Hashes and RedisGears registrations) and install its dependencies with the following command:

```bash
gears-cli run --host <host> --port <port> --password <password> example.py --requirements requirements.txt
```

As rgsync uses the psycopyg2 driver under the covers, please ensure you have the postgresql client libraries (i.e libpq-dev), or the appropriate binary drivers for your operating system installed.

# Test
Using redis-cli perform:
```bash
redis-cli
> hset person:1 first_name foo last_name bar age 20
```
