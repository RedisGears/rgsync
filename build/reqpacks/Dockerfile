
ARG GEARS_VERSION=master

# OSNICK=bionic|stretch|buster
ARG OSNICK=buster

# ARCH=x64|arm64v8|arm32v7
ARG ARCH=x64 

#----------------------------------------------------------------------------------------------
FROM redisfab/redisgears:${GEARS_VERSION}-${ARCH}-${OSNICK}

WORKDIR /build

ADD . /build

RUN	./deps/readies/bin/getpy3
RUN python3 ./build/reqpacks/system-setup.py

CMD ["--loadmodule", "/var/opt/redislabs/lib/modules/redisgears.so"]
