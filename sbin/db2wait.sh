#!/bin/sh

for i in `seq 1 10`; do
    docker logs db2|grep "Setup has completed"
    if [ $? -eq 0 ]; then
        exit 0
    fi
    sleep 60
done
docker logs db2
exit 1
