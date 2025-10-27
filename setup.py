#!/usr/bin/env python

import os
from setuptools import setup, find_namespace_packages


# Read project metadata from pyproject.toml (PEP 621) as the single source of truth.
# If pyproject.toml is missing or invalid, the build will fail.
try:
    import tomllib as _toml  # Python 3.11+
except ImportError:
    import tomli as _toml  # type: ignore

with open("pyproject.toml", "rb") as _f:
    _pyproject_data = _toml.load(_f).get("project", {})

if not _pyproject_data:
    raise ValueError("pyproject.toml is missing [project] section")

# Extract metadata for setup() call (dependencies are read from pyproject by setuptools)
_py_requires = _pyproject_data["requires-python"]
_name = _pyproject_data["name"]
_version = _pyproject_data["version"]
_description = _pyproject_data["description"]

# Extract author info (PEP 621 format: list of dicts with name/email)
_authors = _pyproject_data.get("authors", [])
_author = _authors[0].get("name") if _authors else None
_author_email = _authors[0].get("email") if _authors else None

# Extract URLs
_urls = _pyproject_data.get("urls", {})
_homepage = _urls.get("Homepage")

# Set license directly to avoid setuptools generating non-standard metadata.
# The license is declared via classifiers in pyproject.toml.
_license = "MIT"

# systemd-python is optional (journald / watchdog integration). Kept as extra.

data_dir = os.path.dirname(os.path.realpath(__file__))


def find_file(path):
    return os.path.join(data_dir, path)


with open(find_file("README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name=_name,
    version=_version,
    description=_description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=_author,
    author_email=_author_email,
    url=_homepage,
    license=_license,
    packages=find_namespace_packages(where="src", exclude=("tests", "templates")),
    # map the root package directory to `src/` so find_namespace_packages discovers all
    # nested packages under src/ (including PEP 420 namespace packages).
    package_dir={
        "": "src",
    },
    include_package_data=True,
    package_data={
        "envoxy": [
            # include packaged tools assets
            "tools/*",
            "tools/alembic/*",
            "tools/alembic/alembic/*",
        ]
    },
    python_requires=_py_requires,
)
