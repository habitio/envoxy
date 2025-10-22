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
        import sys
        python_executable = sys.executable
        check_call([python_executable, "uwsgiconfig.py", "--build", "flask"], cwd="src/envoxyd")
        install.run(self)


packages = find_packages(include=["envoxyd", "envoxyd.*"], exclude=["tests", "uwsgi.build"])

"""
Resolve package version for envoxyd from top-level pyproject.toml.

Reads metadata from [tool.vendors.envoxyd] in the repository root pyproject.toml.
If the file or section is missing, the build will fail.
"""

# Read vendor metadata from top-level pyproject.toml
_top_ppath = os.path.normpath(os.path.join(data_dir, '..', 'pyproject.toml'))

try:
    import tomllib as _toml  # Python 3.11+
except ImportError:
    import tomli as _toml  # type: ignore

with open(_top_ppath, 'rb') as _f:
    _pdata = _toml.load(_f)
    _vendor_table = _pdata.get('tool', {}).get('vendors', {}).get('envoxyd', {})

if not _vendor_table:
    raise ValueError(
        f"Missing [tool.vendors.envoxyd] section in {_top_ppath}. "
        "This section is required to build envoxyd."
    )

# Extract metadata from vendor_table (no fallbacks)
_name = _vendor_table["name"]
_version = _vendor_table["version"]
_description = _vendor_table["description"]
_author = _vendor_table.get("author")
_author_email = _vendor_table.get("author-email")
_url = _vendor_table.get("url")
_requires_python = _vendor_table["requires-python"]
_dependencies = _vendor_table["dependencies"]

setup(
    name=_name,
    version=_version,
    description=_description,
    author=_author,
    author_email=_author_email,
    url=_url,
    packages=packages,
    install_requires=_dependencies,
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
    python_requires=_requires_python,
    include_package_data=True,
)
