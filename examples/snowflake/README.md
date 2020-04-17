## Running the recipe
Please use <a href="https://github.com/RedisGears/gears-cli">gears-cli</a> to send a RedisGears Write-Behind and/or Write-Through recipe for execution. For example, run the sample [snowflake](example.py) recipe (contains the mapping of snowflake tables with Redis Hashes and RedisGears registrations) and install its dependencies with the following command:

```bash
gears-cli --host <host> --port <port> --password <password> example.py --requirements requirements.txt
```
