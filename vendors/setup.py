#!/usr/bin/env python

import os
import sys
import shutil
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.build_py import build_py
from setuptools.command.install import install
from subprocess import check_call
import sysconfig


data_dir = os.path.dirname(os.path.realpath(__file__))


def find_file(path):
    return os.path.join(data_dir, path)


class BuildPyWithBinary(build_py):
    """Custom build_py that copies the binary after build_ext runs."""
    
    def run(self):
        # CRITICAL: Force build_ext to run FIRST to compile the binary
        self.run_command('build_ext')
        
        # Run normal build_py
        build_py.run(self)
        
        # After build_ext has run, copy the binary from source to build
        src_binary = os.path.join(data_dir, "envoxyd", "bin", "envoxyd")
        if os.path.exists(src_binary):
            # Copy to build directory so it gets included in the wheel
            dest_dir = os.path.join(self.build_lib, "envoxyd", "bin")
            os.makedirs(dest_dir, exist_ok=True)
            dest_binary = os.path.join(dest_dir, "envoxyd")
            print(f"Copying binary to build: {src_binary} -> {dest_binary}")
            shutil.copy2(src_binary, dest_binary)
            os.chmod(dest_binary, 0o755)
        else:
            print(f"Warning: Binary not found at {src_binary} during build_py")


class BuildEnvoxyD(build_ext):
    """Custom build_ext command that compiles uwsgi during BUILD phase (before wheel creation)."""

    description = "build envoxyd binary"

    def run(self):
        """Build uWSGI binary and copy to package directory."""
        setup_dir = os.path.dirname(os.path.abspath(__file__))
        uwsgi_src_dir = os.path.join(setup_dir, "uwsgi")
        
        if not os.path.exists(uwsgi_src_dir):
            raise RuntimeError(f"uwsgi source directory not found at {uwsgi_src_dir}")
        
        # Copy template files to uwsgi directory (merge, don't overwrite directories)
        templates_dir = os.path.join(setup_dir, "envoxyd", "templates", "uwsgi")
        if os.path.exists(templates_dir):
            print(f"Copying uwsgi templates from {templates_dir}")
            for item in os.listdir(templates_dir):
                src = os.path.join(templates_dir, item)
                dst = os.path.join(uwsgi_src_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    # Merge directories - copy files into existing directory
                    os.makedirs(dst, exist_ok=True)
                    for subitem in os.listdir(src):
                        src_subitem = os.path.join(src, subitem)
                        dst_subitem = os.path.join(dst, subitem)
                        if os.path.isfile(src_subitem):
                            shutil.copy2(src_subitem, dst_subitem)
                        elif os.path.isdir(src_subitem):
                            if os.path.exists(dst_subitem):
                                shutil.rmtree(dst_subitem)
                            shutil.copytree(src_subitem, dst_subitem)
        
        # Also copy run.py to embed/
        run_py_src = os.path.join(setup_dir, "envoxyd", "templates", "run.py")
        if os.path.exists(run_py_src):
            embed_dir = os.path.join(uwsgi_src_dir, "embed")
            os.makedirs(embed_dir, exist_ok=True)
            shutil.copy2(run_py_src, os.path.join(embed_dir, "run.py"))
        
        # Compile uwsgi with flask profile
        print(f"Compiling uwsgi in {uwsgi_src_dir}...")
        print("=" * 80)
        print("IMPORTANT: uwsgi compilation requires:")
        print("  - gcc or clang compiler")
        print("  - Python development headers (python3-dev/python3-devel)")
        print("  - make and other build tools")
        print("=" * 80)
        
        python_executable = sys.executable
        try:
            check_call(
                [python_executable, "uwsgiconfig.py", "--build", "flask"],
                cwd=uwsgi_src_dir
            )
        except Exception as e:
            print("=" * 80)
            print("ERROR: uwsgi compilation failed!")
            print(f"Error: {e}")
            print("=" * 80)
            raise RuntimeError(
                "uwsgi compilation failed. Please ensure build dependencies are installed:\n"
                "  Ubuntu/Debian: sudo apt-get install build-essential python3-dev\n"
                "  RHEL/CentOS: sudo yum install gcc python3-devel\n"
                f"Original error: {e}"
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
            raise RuntimeError(
                "Built uwsgi binary not found after compilation completed. "
                "Expected to find 'envoxyd' or 'uwsgi' in " + uwsgi_src_dir
            )
        
        # Copy binary to package directory (will be included in wheel)
        bin_dir = os.path.join(setup_dir, "envoxyd", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        dest_binary = os.path.join(bin_dir, "envoxyd")
        shutil.copy2(built_binary, dest_binary)
        os.chmod(dest_binary, 0o755)
        print(f"Binary copied to package: {dest_binary}")
        print("uwsgi compilation complete")
        
        # Run parent build_ext
        build_ext.run(self)


class InstallCommand(install):
    """Custom install command that copies the pre-built binary to scripts directory."""

    description = "install envoxyd"

    def run(self):
        """Install package and copy binary to scripts directory."""
        # First run the normal install to set up paths
        install.run(self)
        
        # Try to find the installed package location
        # After install.run(), the package is installed to site-packages
        try:
            import envoxyd
            installed_package_dir = os.path.dirname(envoxyd.__file__)
            
            # The binary should be in the installed package
            src_binary = os.path.join(installed_package_dir, "bin", "envoxyd")
            
            if not os.path.exists(src_binary):
                # If binary doesn't exist, it means build_ext didn't run
                # This can happen with editable installs or if build failed
                print(f"Warning: Binary not found at {src_binary}")
                print("Binary should be built during build phase")
                return
            
            # Install to {prefix}/bin/ (works with venv, user install, system install)
            scripts_dir = sysconfig.get_path('scripts')
            dest_binary = os.path.join(scripts_dir, "envoxyd")
            
            print(f"Installing envoxyd binary to {dest_binary}")
            os.makedirs(scripts_dir, exist_ok=True)
            shutil.copy2(src_binary, dest_binary)
            os.chmod(dest_binary, 0o755)
            print("envoxyd binary installation complete")
        except ImportError:
            # During wheel building, envoxyd is not yet importable
            # This is expected - the binary will be in the wheel's data
            print("Skipping binary installation (wheel build phase)")
            pass


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

# Prepare cmdclass with custom build_ext, build_py and install commands
cmdclass = {
    "build_ext": BuildEnvoxyD,
    "build_py": BuildPyWithBinary,
    "install": InstallCommand,
}

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
            "bin/envoxyd",  # Include the pre-built binary
        ]
    },
    scripts=["envoxyd/tools/envoxy-cli"],
    ext_modules=[
        # Dummy extension to trigger build_ext
        Extension('_envoxyd_build', sources=[])
    ],
    cmdclass=cmdclass,
    python_requires=_requires_python,
    include_package_data=True,
)

