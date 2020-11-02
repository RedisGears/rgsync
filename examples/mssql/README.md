### Prerequisites

Docker compatible [*nix OS](https://en.wikipedia.org/wiki/Unix-like) and Docker installed.
<br>Download this folder and change the *.sh file permissions to 755 i.e. ``` chmod 755 *.sh ```</br>

## Setup Redis Enterprise cluster and database in docker
<br>Execute [setupAndcreate_redb.sh](setupAndcreate_redb.sh)</br>
```bash
./setupAndcreate_redb.sh
```
---
**NOTE**

The above script will create a 3-node Redis Enterprise cluster in docker containers on rg-net network, [Install RedisGears dependencies](https://docs.redislabs.com/latest/modules/redisgears/installing-redisgears/#step-1-install-redisgears-dependencies), [Install RedisGears module](https://docs.redislabs.com/latest/modules/redisgears/installing-redisgears/#step-2-install-the-redisgears-module), [Install MS ODBC driver for MSSQL](https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-ver15#ubuntu17) and [Create a Redis Enterprise database with RedisGears module enabled and verify the installation](https://docs.redislabs.com/latest/modules/redisgears/installing-redisgears/#step-3-create-a-database-and-verify-the-installation).

---

## Setup MSSQL 2017 database in docker
<br>Execute [setup_mssql.sh](setup_mssql.sh)</br>
```bash
./setup_mssql.sh
```
---
**NOTE**

The above script will start a [MSSQL 2017 docker](https://hub.docker.com/layers/microsoft/mssql-server-linux/2017-latest/images/sha256-314918ddaedfedc0345d3191546d800bd7f28bae180541c9b8b45776d322c8c2?context=explore) instance on rg-net network, create RedisGearsTest database and create emp table.

---

# Running the recipe
Please use <a href="https://github.com/RedisGears/gears-cli">gears-cli</a> to send a RedisGears Write-Behind and/or Write-Through recipe for execution. For example, run the sample [MsSql](example.py) recipe (contains the mapping of MsSql tables with Redis Hashes and RedisGears registrations) and install its dependencies with the following command:

```bash
gears-cli run --host <host> --port <port> --password <password> example.py --requirements requirements.txt
```

# Test
Using redis-cli perform:
```bash
redis-cli
> hset emp:1 FirstName foo LastName bar
```

Make sure data reached MsSql server:
```bash
sudo docker exec -it <mssql_container_name> /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P Redis@123
1> use RedisGearsTest
2> go
Changed database context to 'RedisGearsTest'.
1> select * from emp
2> go
empno       fname                                              lname                                             
----------- -------------------------------------------------- --------------------------------------------------
          1 foo                                                bar                                               

(1 rows affected)

```
