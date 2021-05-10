FROM ubuntu:20.04

RUN apt-get update

# base system
RUN apt-get install -y git sudo locales vim gcc make net-tools iputils-ping telnet
RUN DEBIAN_FRONTEND=noninteractive apt-get install software-properties-common -y

RUN add-apt-repository ppa:deadsnakes/ppa

# python dependencies
RUN apt-get install -y python3.6 python3.6-dev python-setuptools python3-setuptools python3-virtualenv libpq-dev
