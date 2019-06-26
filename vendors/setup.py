#!/usr/bin/env python

import os
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.build_py import build_py

from subprocess import check_call, call

import sys
if sys.version_info < (3,6):
    sys.exit('Sorry, Python < 3.6 is not supported')

data_dir = os.path.dirname(os.path.realpath(__file__))

def find_file(path):
    return os.path.join(data_dir, path)

def find_directory(path):
    return os.path.join(data_dir, path, '**/*')

class InstallCommand(install):

    description = "install envoxyd"

    def run(self):
        print('RUNNING INSTALL')
        check_call(["python3", "uwsgiconfig.py",  "--build",  "flask"], cwd='src/envoxyd')
        #check_call(["cp", "envoxyd",  "/usr/local/bin/envoxyd"], cwd='envoxyd/src')
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
    # package_data={
    #     'envoxyd': [],
    # },
    data_files=[
        ('', ['LICENSE.txt', 'src/envoxyd/envoxyd']),
        ('bin', ['src/envoxyd/envoxyd'])
    ],
    cmdclass={
        'install': InstallCommand
    },
    include_package_data=True
)
