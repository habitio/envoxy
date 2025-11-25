#!/usr/bin/env python

import os
import sys
import shutil
from setuptools import setup, find_packages
from setuptools.command.install import install
from subprocess import check_call


data_dir = os.path.dirname(os.path.realpath(__file__))


def find_file(path):
    return os.path.join(data_dir, path)


class InstallCommand(install):
    """Custom install command that compiles uwsgi during installation."""

    description = "install envoxyd"

    def run(self):
        """Build uWSGI and install package."""
        # First run the normal install to set up paths
        install.run(self)
        
        # Now compile and install the binary
        setup_dir = os.path.dirname(os.path.abspath(__file__))
        uwsgi_src_dir = os.path.join(setup_dir, "uwsgi")
        
        if not os.path.exists(uwsgi_src_dir):
            raise RuntimeError(f"uwsgi source directory not found at {uwsgi_src_dir}")
        
        # Copy template files to uwsgi directory
        templates_dir = os.path.join(setup_dir, "envoxyd", "templates", "uwsgi")
        if os.path.exists(templates_dir):
            print(f"Copying uwsgi templates from {templates_dir}")
            for item in os.listdir(templates_dir):
                src = os.path.join(templates_dir, item)
                dst = os.path.join(uwsgi_src_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
        
        # Also copy run.py to embed/
        run_py_src = os.path.join(setup_dir, "envoxyd", "templates", "run.py")
        if os.path.exists(run_py_src):
            embed_dir = os.path.join(uwsgi_src_dir, "embed")
            os.makedirs(embed_dir, exist_ok=True)
            shutil.copy2(run_py_src, os.path.join(embed_dir, "run.py"))
        
        # Compile uwsgi with flask profile
        print(f"Compiling uwsgi in {uwsgi_src_dir}...")
        python_executable = sys.executable
        check_call(
            [python_executable, "uwsgiconfig.py", "--build", "flask"],
            cwd=uwsgi_src_dir
        )
        
        # Find the built binary
        built_binary = None
        for binary_name in ["envoxyd", "uwsgi"]:
            src_binary = os.path.join(uwsgi_src_dir, binary_name)
            if os.path.exists(src_binary):
                built_binary = src_binary
                print(f"Found built binary: {built_binary}")
                break
        
        if not built_binary:
            raise RuntimeError("Built uwsgi binary not found")
        
        # Install to {prefix}/bin/ (works with venv, user install, system install)
        import sysconfig
        scripts_dir = sysconfig.get_path('scripts')
        dest_binary = os.path.join(scripts_dir, "envoxyd")
        
        print(f"Installing envoxyd to {dest_binary}")
        os.makedirs(scripts_dir, exist_ok=True)
        shutil.copy2(built_binary, dest_binary)
        os.chmod(dest_binary, 0o755)
        print("uwsgi compilation and installation complete")


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

# Prepare cmdclass with custom install command
cmdclass = {"install": InstallCommand}

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
    scripts=["envoxyd/tools/envoxy-cli"],
    cmdclass=cmdclass,
    python_requires=_requires_python,
    include_package_data=True,
)

