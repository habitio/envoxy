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
    author='Matheus (vorjdux) Santos',
    author_email='vorj.dux@gmail.com',
    url='https://github.com/habitio/envoxy',
    packages=find_packages(where='src/', exclude=("tests", "templates")),
    install_requires=requirements,
    package_dir={
        'envoxy': 'src/envoxy'
    },
    package_data={
        'envoxy': [
            find_file('LICENSE.txt'),
            find_file('requirements.txt'),
            find_file('etc/envoxy/envoxy-base.json')
        ],
        'envoxyd': [
            'bin/*'
        ]
    },
    data_files=[('', ['LICENSE.txt', 'requirements.txt'])]
)
