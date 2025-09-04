"""Generic Alembic environment for the framework.

This env.py attempts to discover models automatically using an environment
variable SERVICE_MODELS. If that's not set, it will scan a known set of
locations under the repository to import modules named `models`.

It exposes `target_metadata` for autogenerate and keeps the alembic runtime
lightweight so services don't have to provide their own env.py unless they
need custom logic.
"""
from __future__ import annotations

import importlib
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides access to the values within
# the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add repository src and repo root to path so rendering modules are importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC_PATH = os.path.join(REPO_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Strategy: prefer SERVICE_MODELS env var; otherwise scan common locations.
SERVICE_MODELS = os.environ.get('SERVICE_MODELS')
_candidates = []
if SERVICE_MODELS:
    _candidates = [SERVICE_MODELS]
else:
    # Look for top-level packages under repo that might contain models
    for p in ('examples', 'src'):
        base = os.path.join(REPO_ROOT, p)
        if os.path.isdir(base):
            for entry in os.listdir(base):
                candidate = f"{p}.{entry}.models"
                _candidates.append(candidate)

# Try importing the candidates in order and collect metadata
target_metadata = None
for candidate in _candidates:
    try:
        module = importlib.import_module(candidate)
        # If the module exposes metadata, prefer it; otherwise look for EnvoxyBase
        if hasattr(module, 'metadata'):
            target_metadata = getattr(module, 'metadata')
            break
        # fallback: try to import envoxy.db.orm and use its metadata
    except Exception:
        # ignore import errors and try next candidate
        continue

# As a last resort, try framework-level EnvoxyBase.metadata
if target_metadata is None:
    try:
        from envoxy.db.orm import EnvoxyBase

        target_metadata = EnvoxyBase.metadata
    except Exception:
        target_metadata = None


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
