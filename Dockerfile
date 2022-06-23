FROM envoxy-ubuntu:18.04

RUN useradd -ms /bin/bash envoxy

# source dir for envoxy code and project
RUN mkdir -p /usr/envoxy
WORKDIR /usr/envoxy

# envoxy user
ADD . /usr/envoxy

RUN make install

EXPOSE 8080 8080

workdir /home/envoxy
