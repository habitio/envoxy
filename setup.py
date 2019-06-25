#!/usr/bin/env python

import os
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.build_py import build_py

from subprocess import check_call, call

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


class BuildCommand(build_py):

    description = "prepare files to build envoxyd"

    def run(self):
        try:
            check_call(["rm -rf src/envoxyd"], shell=True)
        except :
            pass
        check_call(["mkdir -p src/envoxyd"], shell=True)
        check_call(["cp -R vendors/uwsgi/* src/envoxyd"], shell=True)
        check_call(["cp -R etc/uwsgi/* src/envoxyd/"], shell=True)
        check_call(["export UWSGI_PROFILE='buildconf/flask.ini'"], shell=True)
        call("python3 uwsgiconfig.py --build flask", cwd='src/envoxyd', shell=True)
        check_call(["cp src/envoxyd/envoxyd etc/envoxyd"], shell=True)

        build_py.run(self)

setup(
    name='envoxy',
    version='0.0.2',
    description='Envoxy Platform Framework',
    author='Matheus Santos',
    author_email='vorj.dux@gmail.com',
    url='https://github.com/muzzley/envoxy',
    packages=find_packages(where='src/', exclude=("tests", "templates", "envoxyd")),
    install_requires=requirements,
    package_dir={
        'envoxy': 'src/envoxy',
        # 'envoxyd': 'src/envoxyd'
    },
    package_data={
        'envoxy': [
            find_file('LICENSE.txt'),
            find_file('requirements.txt'),
            find_file('etc/envoxy/envoxy-base.json'),
            find_file('etc/envoxyd'),
            # find_file('etc/uwsgi/buildconf/flask.ini'),
            # find_file('etc/uwsgi/envoxy/flaskconfig.ini'),
            # find_file('etc/uwsgi/envoxy/envoxyd.py'),
            # find_file('etc/uwsgi/envoxy/bootstrap.py')
        ],
        # 'envoxyd': [
        #     find_file('LICENSE.txt'),
        #     find_file('requirements.txt'),
        #     find_file('etc/envoxy/envoxy-base.json'),
        #     find_file('etc/uwsgi/buildconf/flask.ini'),
        #     find_file('etc/uwsgi/envoxy/flaskconfig.ini'),
        #     find_file('etc/uwsgi/envoxy/envoxyd.py'),
        #     find_file('etc/uwsgi/envoxy/bootstrap.py')
        # ]
    },
    data_files=[('', ['LICENSE.txt', 'requirements.txt'])],
    cmdclass={
        'build_py': BuildCommand
    },
)
