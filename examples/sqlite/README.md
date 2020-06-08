# Connect the DB

## Install SQLite (on ubuntu)
### Ubuntu
```bash
sudo apt-get install sqlite3 libsqlite3-dev
```

### CentOS
```bash
yum install sqlite
```

## Create Persons table
Run `sqlite3 /tmp/mydatabase.db` and create the `persons` table with the folowing line:
```bash
sqlite> CREATE TABLE persons (person_id VARCHAR(100) NOT NULL, first VARCHAR(100) NOT NULL, last VARCHAR(100) NOT NULL, age INT NOT NULL, PRIMARY KEY (person_id));
```

# Running the recipe
Please use <a href="https://github.com/RedisGears/gears-cli">gears-cli</a> to send a RedisGears Write-Behind and/or Write-Through recipe for execution. For example, run the sample [SQLite](example.py) recipe (contains the mapping of sqlite tables with Redis Hashes and RedisGears registrations) and install its dependencies with the following command:

```bash
gears-cli run --host <host> --port <port> --password <password> example.py --requirements requirements.txt
```
