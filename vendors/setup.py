#!/usr/bin/env python

import os
import sys
from setuptools import setup, find_packages
try:
    from wheel.bdist_wheel import bdist_wheel
    _HAS_WHEEL = True
except Exception:
    _HAS_WHEEL = False
from setuptools.command.install import install

from subprocess import check_call


data_dir = os.path.dirname(os.path.realpath(__file__))


def find_file(path):
    return os.path.join(data_dir, path)


class InstallCommand(install):

    description = "install envoxyd"

    def run(self):
        """Build uWSGI and install package."""
        # Get the directory where this setup.py lives
        setup_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(setup_dir, "src", "envoxyd")
        envoxyd_binary = os.path.join(data_dir, "envoxyd")
        
        # Skip uWSGI compilation if binary already exists (e.g., pre-built by Dockerfile)
        # OR if running under cibuildwheel (which will compile in CIBW_BEFORE_BUILD)
        skip_compilation = os.path.exists(envoxyd_binary) or os.environ.get('CIBUILDWHEEL', '0') == '1'
        
        if not skip_compilation:
            print("Compiling uWSGI...")
            python_executable = sys.executable
            uwsgi_dir = os.path.join(setup_dir, "src", "envoxyd")
            check_call([python_executable, "uwsgiconfig.py", "--build", "flask"], cwd=uwsgi_dir)
        else:
            if os.environ.get('CIBUILDWHEEL'):
                print("Skipping uWSGI compilation (will be built by CIBW_BEFORE_BUILD)")
            else:
                print(f"Skipping uWSGI compilation (binary exists at {envoxyd_binary})")
        
        install.run(self)


packages = find_packages(include=["envoxyd", "envoxyd.*"], exclude=["tests", "uwsgi.build"])

"""
Resolve package metadata for envoxyd from local pyproject.toml.

Reads metadata from [project] section in vendors/pyproject.toml.
"""

# Read metadata from local pyproject.toml (in same directory as this setup.py)
_local_ppath = os.path.join(data_dir, 'pyproject.toml')

try:
    import tomllib as _toml  # Python 3.11+
except ImportError:
    import tomli as _toml  # type: ignore

if not os.path.exists(_local_ppath):
    raise ValueError(
        f"Missing pyproject.toml in {data_dir}. "
        "This file is required to build envoxyd."
    )

with open(_local_ppath, 'rb') as _f:
    _pdata = _toml.load(_f)
    _project_table = _pdata.get('project', {})

if not _project_table:
    raise ValueError(
        f"Missing [project] section in {_local_ppath}. "
        "This section is required to build envoxyd."
    )

# Extract metadata from project table
_name = _project_table["name"]
_version = _project_table["version"]
_description = _project_table["description"]
_requires_python = _project_table["requires-python"]
_dependencies = _project_table["dependencies"]

# Extract author info from authors array
_authors = _project_table.get("authors", [])
_author = _authors[0].get("name") if _authors else None
_author_email = _authors[0].get("email") if _authors else None

# Extract URL from project.urls
_urls = _project_table.get("urls", {})
_url = _urls.get("Homepage")

# License from classifiers
_project_license = "MIT"

if _HAS_WHEEL:
    class NonPureWheel(bdist_wheel):
        def finalize_options(self):
            bdist_wheel.finalize_options(self)
            # Force wheel metadata to indicate non-pure since this package
            # installs compiled/native files into data_files.
            self.root_is_pure = False

# Prepare cmdclass ensuring 'install' is preserved and optionally
# register the NonPureWheel for bdist_wheel when wheel is available.
cmdclass = {"install": InstallCommand}
if _HAS_WHEEL:
    cmdclass["bdist_wheel"] = NonPureWheel

# Conditionally include the uWSGI binary in data_files only if it exists.
# During cibuildwheel, CIBW_BEFORE_BUILD should have built and placed the binary.
# For local dev builds, the InstallCommand will build it before install_data runs.
_data_files = [
    ("bin", ["envoxyd/tools/envoxy-cli"]),
]
_envoxyd_binary_path = "src/envoxyd/envoxyd"
if os.path.exists(_envoxyd_binary_path):
    _data_files.insert(0, ("bin", [_envoxyd_binary_path]))
else:
    # When CIBUILDWHEEL is set, the binary should exist (built by CIBW_BEFORE_BUILD).
    # If it doesn't, log a warning but continue (the install step will handle it).
    if os.environ.get('CIBUILDWHEEL'):
        print(f"WARNING: {_envoxyd_binary_path} not found but CIBUILDWHEEL is set. "
              "Ensure CIBW_BEFORE_BUILD built the binary.")

setup(
    name=_name,
    version=_version,
    description=_description,
    author=_author,
    author_email=_author_email,
    url=_url,
    license=_project_license,
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
    data_files=_data_files,
    cmdclass=cmdclass,
    python_requires=_requires_python,
    include_package_data=True,
)
