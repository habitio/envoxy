Generic framework Alembic

This folder provides a generic alembic configuration and environment that
framework services can reuse without creating a per-service `alembic.ini` or
`env.py`.

How it works:
- The framework-level `tools/alembic/alembic.ini` and `tools/alembic/alembic/env.py`
  attempt to discover `models` modules in common locations (via the
  `SERVICE_MODELS` env var or by scanning `examples/*/models` and similar).
- Service helper scripts (e.g. `examples/*/alembic/alembic.sh`) prefer a
  per-service `alembic.ini` but fall back to this framework config if absent.

To use the generic config for a service without a custom `alembic.ini`:

  PYTHONPATH=src SERVICE_MODELS=your.service.models \
    examples/consumer_module/alembic/alembic.sh revision -m "message"

To override, create a per-service `alembic.ini` next to the helper script and
`alembic.sh` will prefer it.
