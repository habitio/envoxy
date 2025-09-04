from __future__ import annotations

import importlib
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

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


# Make sqlite relative paths in the alembic config absolute relative to the
# config file location. This prevents "unable to open database file" when
# running the alembic helper from a different working directory.
cfg_file = config.config_file_name
if cfg_file:
    try:
        cfg_dir = os.path.dirname(os.path.abspath(cfg_file))
        url = config.get_main_option('sqlalchemy.url')
        if url and url.startswith('sqlite:///'):
            # strip the scheme (sqlite:///)
            db_path = url[len('sqlite:///'):]
            if not os.path.isabs(db_path):
                abs_db = os.path.normpath(os.path.join(cfg_dir, db_path))
                # ensure parent dir exists so sqlite can create the file
                parent = os.path.dirname(abs_db)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent, exist_ok=True)
                new_url = f"sqlite:///{abs_db}"
                config.set_main_option('sqlalchemy.url', new_url)
    except Exception:
        # best-effort: if anything fails here, let alembic continue and
        # surface the original error to the user
        pass


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
