#!/usr/bin/env python

import os
from setuptools import setup, find_packages

import sys
if sys.version_info < (3,6):
    sys.exit('Sorry, Python < 3.6 is not supported')

try:
    with open('./requirements.txt') as f:
        requirements = f.read().splitlines()
except Exception as e:
    requirements = []

data_dir = os.path.dirname(os.path.realpath(__file__))

def find_file(path):
    return os.path.join(data_dir, path)

with open(find_file('README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='envoxy',
    version='0.1.10',
    description='Envoxy Platform Framework',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Matheus (vorjdux) Santos',
    author_email='vorj.dux@gmail.com',
    url='https://github.com/habitio/envoxy',
    packages=find_packages(where='src/', exclude=("tests", "templates")),
    install_requires=requirements,
    package_dir={
        'envoxy': 'src/envoxy',
    },
    package_data={
        'envoxy': [
            find_file('LICENSE'),
            find_file('requirements.txt'),
        ]
    },
    data_files=[('envoxy', ['LICENSE', 'requirements.txt'])]
)
