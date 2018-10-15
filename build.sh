#!/bin/bash

# Try to install packages function
try_install() {
    sudo dpkg -l "$1" | grep -q ^ii && return 1
    sudo apt-get -y install "$@"
    return 0
}

# Trying to install packages
try_install debhelper
try_install dh-virtualenv
try_install dh-python
try_install python-setuptools
try_install python3-setuptools
try_install python3-all
try_install python3-pip

# Trying to install the python packages
sudo pip3.6 install -r requirements.txt

# Remove all generated dist files previously
sudo rm -rf deb_dist dist envoxy-*.tar.gz envoxy.egg-info

# Packing the project in debian package
sudo python3.6 setup.py --command-packages=stdeb.command bdist_deb
