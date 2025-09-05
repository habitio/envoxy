from __future__ import annotations

import importlib
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC_PATH = os.path.join(REPO_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

SERVICE_MODELS = os.environ.get('SERVICE_MODELS')
_candidates = []
if SERVICE_MODELS:
    _candidates = [SERVICE_MODELS]
else:
    # try local example package
    _candidates = ['examples.template_service.models']

target_metadata = None
for candidate in _candidates:
    try:
        module = importlib.import_module(candidate)
        if hasattr(module, 'metadata'):
            target_metadata = getattr(module, 'metadata')
            break
    except Exception:
        continue

if target_metadata is None:
    try:
        from envoxy.db.orm import EnvoxyBase
        target_metadata = EnvoxyBase.metadata
    except Exception:
        target_metadata = None


# Enforce Postgres URL presence (placeholder in ini must be overridden)
url_check = config.get_main_option('sqlalchemy.url')
if not url_check.startswith('postgresql://'):
    raise RuntimeError('PostgreSQL sqlalchemy.url required (got placeholder or non-postgres URL)')


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
