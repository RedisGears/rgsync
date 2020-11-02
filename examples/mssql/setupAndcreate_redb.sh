#!/bin/bash
# Delete bridge network if it already exist
sudo docker network rm rg-net 2>/dev/null
sudo docker kill re-node1;sudo docker rm re-node1;
sudo docker kill re-node2;sudo docker rm re-node2;
sudo docker kill re-node3;sudo docker rm re-node3;
# Uncomment this to pull the newer version of redislabs/redis docker image in case the latest tag has been upgraded
#sudo docker rmi -f $(docker images | grep redislabs | awk '{print $3}')

# Create a bridge network for RE and MSSQL containers
echo "Creating bridge network..."
sudo docker network create --driver bridge rg-net
# Start 3 docker containers. Each container is a node in the same network
echo "Starting Redis Enterprise as Docker containers..."
sudo docker run -d --cap-add sys_resource -h re-node1 --name re-node1 -p 18443:8443 -p 19443:9443 -p 14000-14005:12000-12005 -p 18070:8070 --network rg-net redislabs/redis:latest
sudo docker run -d --cap-add sys_resource -h re-node2 --name re-node2 -p 28443:8443 -p 29443:9443 -p 12010-12015:12000-12005 -p 28070:8070 --network rg-net redislabs/redis:latest
sudo docker run -d --cap-add sys_resource -h re-node3 --name re-node3 -p 38443:8443 -p 39443:9443 -p 12020-12025:12000-12005 -p 38070:8070 --network rg-net redislabs/redis:latest
# Create Redis Enterprise cluster
echo "Waiting for the servers to start..."
sleep 60
echo "Creating Redis Enterprise cluster and joining nodes..."
sudo docker exec -it --privileged re-node1 "/opt/redislabs/bin/rladmin" cluster create name re-cluster.local username demo@redislabs.com password redislabs
sudo docker exec -it --privileged re-node2 "/opt/redislabs/bin/rladmin" cluster join nodes $(sudo docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' re-node1) username demo@redislabs.com password redislabs
sudo docker exec -it --privileged re-node3 "/opt/redislabs/bin/rladmin" cluster join nodes $(sudo docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' re-node1) username demo@redislabs.com password redislabs
echo ""
# Test the cluster 
sudo docker exec -it re-node1 bash -c "/opt/redislabs/bin/rladmin info cluster"

# Install wget to download RedisGears components
echo "Installing RedisGears and it's prerequisites..."
sudo docker exec --user root -it re-node1 bash -c "apt-get install -y wget"
sudo docker exec --user root -it re-node2 bash -c "apt-get install -y wget"
sudo docker exec --user root -it re-node3 bash -c "apt-get install -y wget"
rm install_gears.sh
tee -a install_gears.sh <<EOF
wget http://redismodules.s3.amazonaws.com/redisgears/redisgears.linux-bionic-x64.1.0.2.zip
wget http://redismodules.s3.amazonaws.com/redisgears/redisgears-dependencies.linux-bionic-x64.1.0.2.tgz
wget http://redismodules.s3.amazonaws.com/rgsync/rgsync-1.0.1.linux-bionic-x64.zip

mkdir -p /var/opt/redislabs/modules/rg/10002/deps/
tar -xvf redisgears-dependencies.linux-bionic-x64.1.0.2.tgz -C /var/opt/redislabs/modules/rg/10002/deps
chown -R redislabs /var/opt/redislabs/modules/rg

curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && curl https://packages.microsoft.com/config/ubuntu/18.04/prod.list > /etc/apt/sources.list.d/mssql-release.list 
sudo apt-get update -y
echo msodbcsql17 msodbcsql/ACCEPT_EULA boolean true | sudo debconf-set-selections
apt-get install -y msodbcsql17
ACCEPT_EULA=Y apt-get install -y mssql-tools
echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile
echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc
source ~/.bashrc
apt-get install -y unixodbc-dev
EOF

sudo docker cp install_gears.sh re-node1:/opt/install_gears.sh
sudo docker exec --user root -it re-node1 bash -c "chmod 777 /opt/install_gears.sh"
sudo docker exec --user root -it re-node1 bash -c "/opt/install_gears.sh"
sudo docker cp install_gears.sh re-node2:/opt/install_gears.sh
sudo docker exec --user root -it re-node2 bash -c "chmod 777 /opt/install_gears.sh"
sudo docker exec --user root -it re-node2 bash -c "/opt/install_gears.sh"
sudo docker cp install_gears.sh re-node3:/opt/install_gears.sh
sudo docker exec --user root -it re-node3 bash -c "chmod 777 /opt/install_gears.sh"
sudo docker exec --user root -it re-node3 bash -c "/opt/install_gears.sh"

echo "Uploading RedisGears module..."
rm upload_rg.sh
tee -a upload_rg.sh <<EOF
curl -v -k -u demo@redislabs.com:redislabs -F "module=@./redisgears.linux-bionic-x64.1.0.2.zip" https://localhost:9443/v1/modules
EOF
sudo docker cp upload_rg.sh re-node1:/opt/upload_rg.sh
sudo docker exec --user root -it re-node1 bash -c "chmod 777 /opt/upload_rg.sh"
sudo docker exec --user root -it re-node1 bash -c "/opt/upload_rg.sh"

sleep 15
echo "Creating databases..."
rm create_demodb.sh
tee -a create_demodb.sh <<EOF
curl -v -k -L -u demo@redislabs.com:redislabs --location-trusted -H Content-type:application/json -d '{ "name": "RedisGears-db", "port": 12000, "memory_size": 1000000000, "type" : "redis", "replication": false, "module_list": [ {"module_args": "CreateVenv 1 DownloadDeps 0", "module_id": "0244462f3a972c5c52ae0e4d2c631624", "module_name": "rg", "semantic_version": "1.0.2"} ] }' https://localhost:9443/v1/bdbs
EOF
sudo docker cp create_demodb.sh re-node1:/opt/create_demodb.sh
sudo docker exec --user root -it re-node1 bash -c "chmod 777 /opt/create_demodb.sh"
sudo docker exec --user root -it re-node1 bash -c "/opt/create_demodb.sh"
echo ""

echo "Database port mappings per node. We are using mDNS so use the IP and exposed port to connect to the databases."
echo "node1:"
sudo docker port re-node1 | grep "12000"
echo "node2:"
sudo docker port re-node2 | grep "12000"
echo "node3:"
sudo docker port re-node3 | grep "12000"
sleep 10
# Test database with RedisGears module
echo "------------- RedisGears status -------------"
sudo docker exec -it re-node1 bash -c "redis-cli -p 12000 RG.PYEXECUTE 'GearsBuilder().run()'"
echo "------------- RLADMIN status -------------"
sudo docker exec -it re-node1 bash -c "rladmin status"
echo ""
echo "Now open the browser and access Redis Enterprise Admin UI at https://127.0.0.1:18443 with username=demo@redislabs.com and password=redislabs."
echo "To connect using RedisInsight or redis-cli, please use the exposed port from the node where master shard for the database resides."
echo "DISCLAIMER: This is best for local development or functional testing. Please see, https://docs.redislabs.com/latest/rs/getting-started/getting-started-docker"
