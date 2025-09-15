#!/usr/bin/env python

import os
from setuptools import setup, find_namespace_packages

import sys

try:
    with open("./requirements.txt") as f:
        requirements = f.read().splitlines()
except Exception as e:
    requirements = []

# systemd-python is optional (journald / watchdog integration). Kept as extra.

data_dir = os.path.dirname(os.path.realpath(__file__))


def find_file(path):
    return os.path.join(data_dir, path)


with open(find_file("README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="envoxy",
    version="0.4.4",
    description="Envoxy Platform Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Matheus (vorjdux) Santos",
    author_email="vorj.dux@gmail.com",
    url="https://github.com/habitio/envoxy",
    packages=find_namespace_packages(where="src", exclude=("tests", "templates")),
    install_requires=requirements,
    extras_require={
        "journald": ["systemd-python>=235"],
    },
    # map the root package directory to `src/` so find_namespace_packages discovers all
    # nested packages under src/ (including PEP 420 namespace packages).
    package_dir={
        "": "src",
    },
    include_package_data=True,
    package_data={
        "envoxy": [
            find_file("LICENSE"),
            find_file("requirements.txt"),
            # include packaged tools assets
            "tools/*",
            "tools/alembic/*",
            "tools/alembic/alembic/*",
        ]
    },
    entry_points={
        "console_scripts": [
            "envoxy-alembic = envoxy.tools.alembic.cli:main",
        ],
    },
    python_requires=">=3.11",
    data_files=[("envoxy", ["LICENSE", "requirements.txt"])],
)
