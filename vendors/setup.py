#!/usr/bin/env python

import os
from setuptools import setup, find_packages
from setuptools.command.install import install

from subprocess import check_call

import sys
if sys.version_info < (3,6):
    sys.exit('Sorry, Python < 3.6 is not supported')

data_dir = os.path.dirname(os.path.realpath(__file__))

def find_file(path):
    return os.path.join(data_dir, path)

class InstallCommand(install):

    description = "install envoxyd"

    def run(self):
        check_call(["python3", "uwsgiconfig.py",  "--build",  "flask"], cwd='src/envoxyd')
        install.run(self)

setup(
    name='envoxyd',
    version='0.0.1',
    description='Envoxyd',
    author='Matheus Santos',
    author_email='vorj.dux@gmail.com',
    url='https://github.com/muzzley/envoxy',
    packages=find_packages(exclude=["uwsgi"]),
    install_requires=[
        "envoxy==0.0.3"
    ],
    package_dir={
        'envoxyd': 'envoxyd/',
    },
    data_files=[
        ('envoxyd', ['LICENSE.txt']),
        ('bin', ['src/envoxyd/envoxyd'])
    ],
    cmdclass={
        'install': InstallCommand
    },
    include_package_data=True
)
