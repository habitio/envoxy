from __future__ import with_statement

import sys
from logging.config import fileConfig

from alembic import context

from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None


def process_revision_directives(context_, revision, directives):
    """Called by Alembic during `revision --autogenerate`.

    This hook attempts to call our envoxy autogenerate checker. It is
    intentionally tolerant: if the checker cannot run, it will not
    abort autogeneration (so developer flow isn't blocked by config).
    """
    try:
        if getattr(context_, 'opts', None) and context_.opts.get('autogenerate', False):
            # try to import our checker and call it with the autogeneration context
            try:
                from envoxy.tools.alembic_hooks import check_autogenerate_revision
            except Exception:
                return

            # some alembic versions expose the autogenerate RevisionContext
            # on the 'revision_context' attribute of the passed in context_ (best-effort)
            rev_ctx = getattr(context_, 'revision_context', None)
            if rev_ctx is not None:
                try:
                    check_autogenerate_revision(rev_ctx)
                except Exception:
                    # re-raise to make the autogenerate fail
                    raise
            else:
                # As a fallback, try to use directives[0].
                try:
                    rc = getattr(directives[0], 'revision_context', None)
                    if rc is not None:
                        check_autogenerate_revision(rc)
                except Exception:
                    # best-effort only
                    raise
    except Exception:
        raise


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
