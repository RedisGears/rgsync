## Running the recipe

### Install SQLite (on ubuntu)
```bash
sudo apt-get install sqlite3 libsqlite3-dev
```

### Create Persons table
Run `sqlite3 < db file path >` and create the `persons` table with the folowing line:
```bash
sqlite> CREATE TABLE persons (person_id VARCHAR(100) NOT NULL, first VARCHAR(100) NOT NULL, last VARCHAR(100) NOT NULL, age INT NOT NULL, PRIMARY KEY (person_id));
```

### Run the Recipe
Use [this utility](https://github.com/RedisGears/RedisGears/blob/master/recipes/gears.py) to send a RedisGears Write-Behind recipe.

```bash
python gears.py --host <host> --port <port> --password <password> examples/sqlite/example.py REQUIREMENTS rgsync
```
