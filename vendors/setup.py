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
        check_call(["python3.11", "uwsgiconfig.py", "--build", "flask"], cwd="src/envoxyd")
        install.run(self)


packages = find_packages(include=["envoxyd", "envoxyd.*"], exclude=["tests", "uwsgi.build"])

setup(
    name="envoxyd",
    version="0.3.3",
    description="Envoxyd",
    author="Matheus Santos",
    author_email="vorj.dux@gmail.com",
    url="https://github.com/muzzley/envoxy",
    packages=packages,
    install_requires=["envoxy>=0.4.3", "flask-cors==6.0.0", "isort>=4.2.5,<5"],
    package_dir={
        "envoxyd": "envoxyd/",
    },
    # console_scripts not defined because envoxy-cli is a bash script distributed via data_files/bin
    package_data={
        "envoxyd": [
            "templates/run.py",
            "templates/view.py",
            "templates/confs/envoxy.json",
            "tools/*",
            "templates/__init__.py",
            "templates/confs/__init__.py",
        ]
    },
    data_files=[
        ("bin", ["src/envoxyd/envoxyd"]),
        ("bin", ["envoxyd/tools/envoxy-cli"]),
        ("envoxyd", ["LICENSE.txt"]),
    ],
    cmdclass={"install": InstallCommand},
    python_requires=">=3.11",
    include_package_data=True,
)
