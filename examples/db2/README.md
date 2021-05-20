# Prerequisites

Docker compatible [*nix OS](https://en.wikipedia.org/wiki/Unix-like) and Docker installed.
<br>Download this folder and give execute permission to the scripts i.e.</br>
```bash
wget -c https://github.com/RedisGears/rgsync/archive/master.zip && unzip master.zip "rgsync-master/examples/mssql/*" && rm master.zip && mv rgsync-master rgsync && cd rgsync/examples/mssql && chmod a+x *.sh
```

## Setup DB2

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
