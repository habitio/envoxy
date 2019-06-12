FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y git sudo locales vim gcc make

RUN mkdir -p /usr/envoxy
WORKDIR /usr/envoxy

ADD . /usr/envoxy

# Set the locale
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN useradd -ms /bin/bash envoxy

RUN ./.build install


