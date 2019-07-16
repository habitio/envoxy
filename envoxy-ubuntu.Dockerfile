FROM ubuntu:18.04

RUN apt-get update

# base system
RUN apt-get install -y git sudo locales vim gcc make net-tools iputils-ping telnet

# python dependencies
RUN apt-get install -y python3.6-dev python-setuptools python3-setuptools python-virtualenv python3-virtualenv libpq-dev
