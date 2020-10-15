# Set up MySql DB

## Setup MySql docker
```bash
docker run -p 3306:3306 --name some-mysql -e MYSQL_ROOT_PASSWORD=my-secret-pw -d mysql:latest
```

## Create Persons table
```bash
docker exec -it <mysql container id> /bin/bash
mysql -u root -p # set password my-secret-pw
CREATE DATABASE test;
CREATE TABLE test.persons (person_id VARCHAR(100) NOT NULL, first VARCHAR(100) NOT NULL, last VARCHAR(100) NOT NULL, age INT NOT NULL, PRIMARY KEY (person_id));
CREATE USER 'demouser'@'%' IDENTIFIED BY 'Password123!';
FLUSH PRIVILEGES;
GRANT ALL PRIVILEGES ON test.* to 'demouser'@'%';
FLUSH PRIVILEGES;
```

# Running the recipe
Assuming you have RedisGears up and running. Please use <a href="https://github.com/RedisGears/gears-cli">gears-cli</a> to send a RedisGears Write-Behind and/or Write-Through recipe for execution. For example, run the sample [MySql](example.py) recipe (contains the mapping of MySql tables with Redis Hashes and RedisGears registrations) and install its dependencies with the following command:

```bash
gears-cli run --host <host> --port <port> --password <password> example.py --requirements requirements.txt
```

# Test
Using redis-cli perform:
```bash
hset person:1 first_name foo last_name bar age 20
```

Make sure data reached MySql server:
```bash
docker exec -it <mysql container id> /bin/bash
mysql -u root -p # set password my-secret-pw
mysql> select * from test.persons;
+-----------+-------+------+-----+
| person_id | first | last | age |
+-----------+-------+------+-----+
| 1         | foo   | bar  |  20 |
+-----------+-------+------+-----+
1 row in set (0.00 sec)

```