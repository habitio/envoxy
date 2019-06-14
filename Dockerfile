FROM muzzley-ubuntu:18.04

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN useradd -ms /bin/bash envoxy

# source dir for envoxy code and project
RUN mkdir -p /usr/envoxy
WORKDIR /usr/envoxy

# envoxy user
ADD . /usr/envoxy

RUN ./.build install

EXPOSE 8080 8080