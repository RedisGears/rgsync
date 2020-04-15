## Running the recipe
You can use [this utility](https://github.com/RedisGears/RedisGears/blob/master/recipes/gears.py) to send a RedisGears Write-Behind or Write-Through recipe for execution. For example, run this repository's [example.py recipe](https://github.com/rgsync/examples/snowflake/example.py) and install its dependencies with the following command:

```bash
python gears.py --host <host> --port <port> --password <password> examples/snowflake/example.py REQUIREMENTS rgsync snowflake-sqlalchemy
```
