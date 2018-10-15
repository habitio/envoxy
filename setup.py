#!/usr/bin/env python

import os
from setuptools import setup, find_packages

try:
    with open('./requirements.txt') as f:
        requirements = f.read().splitlines()
except Exception as e:
    requirements = []

data_dir = os.path.dirname(os.path.realpath(__file__))

def find_file(path):
    return os.path.join(data_dir, path)

setup(
    name='envoxy',
    version='0.0.1',
    description='Envoxy Platform Framework',
    author='Matheus Santos',
    author_email='vorj.dux@gmail.com',
    url='https://github.com/muzzley/envoxy',
    packages=find_packages(exclude=("tests",)),
    install_requires=requirements,
    package_data={
        '': [
            find_file('LICENSE.txt'),
            find_file('requirements.txt'),
            find_file('etc/envoxy/envoxy-base.json')
        ]
    },
    data_files=[
        ('', ['LICENSE.txt', 'requirements.txt']),
		('/etc/envoxy', ['etc/envoxy/envoxy-base.json'])
    ]
)