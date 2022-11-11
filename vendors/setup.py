#!/usr/bin/env python

import os
from setuptools import setup, find_packages
from setuptools.command.install import install

from subprocess import check_call

data_dir = os.path.dirname(os.path.realpath(__file__))

def find_file(path):
    return os.path.join(data_dir, path)

class InstallCommand(install):

    description = "install envoxyd"

    def run(self):
        check_call(["python3", "uwsgiconfig.py", "--build", "flask"], cwd='src/envoxyd')
        install.run(self)

setup(
    name='envoxyd',
    version='0.1.1',
    description='Envoxyd',
    author='Matheus Santos',
    author_email='vorj.dux@gmail.com',
    url='https://github.com/muzzley/envoxy',
    packages=find_packages(exclude=["uwsgi", "templates", "tests"]),
    install_requires=[
        "envoxy>=0.2.1",
        "flask_cors==3.0.9",
        "isort>=4.2.5,<5"
    ],
    package_dir={
        'envoxyd': 'envoxyd/',
    },
    data_files=[
        ('bin', ['src/envoxyd/envoxyd']),
        ('bin', ['envoxyd/tools/envoxy-cli']),
        ('envoxyd', ['LICENSE.txt']),
        ('envoxyd/etc/templates', ['envoxyd/templates/__init__.py']),
        ('envoxyd/etc/templates', ['envoxyd/templates/run.py']),
        ('envoxyd/etc/templates/confs', ['envoxyd/templates/confs/envoxy.json']),
        ('envoxyd/etc/templates/views', ['envoxyd/templates/view.py'])
    ],
    cmdclass={
        'install': InstallCommand
    },
    python_requires='>=3.6',
    include_package_data=True
)
