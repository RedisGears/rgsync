#!/bin/bash
  
# delete the existing mssql2017 container if it exist
sudo docker kill mssql2017-$(hostname);sudo docker rm mssql2017-$(hostname);

network=$(sudo docker network ls | grep rg-net | awk '{print $2}')
if [ -z "$network" ]
then
        echo "rg-net network does not exist. Skip creating rg-net network."
        echo "Creating mssql2017-$(hostname) docker container."
        sudo docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=Redis@123" -e "MSSQL_AGENT_ENABLED=true" -p 1433:1433 --name mssql2017-$(hostname) -d microsoft/mssql-server-linux:2017-latest
else
        echo "Using existing rg-net network to communicate with Redis Enterprise docker containers."
        echo "Creating mssql2017-$(hostname) docker container."
        sudo docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=Redis@123" -e "MSSQL_AGENT_ENABLED=true" -p 1433:1433 --network rg-net --name mssql2017-$(hostname) -d microsoft/mssql-server-linux:2017-latest
fi

sleep 30s

echo "Creating RedisGearsTest database and emp table."
#run the setup script to create the DB and the table in the DB
sudo docker cp mssql_init.sql mssql2017-$(hostname):mssql_init.sql
sudo docker exec -it mssql2017-$(hostname) /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "Redis@123" -i mssql_init.sql
echo ""
