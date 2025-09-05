Template service example
========================

Minimal layout showing how to use the packaged Alembic environment provided
by `envoxy` without copying `alembic.ini` or `env.py`.

Key files:
* `models.py` – imports model classes and exposes `metadata`
* `product.py` – sample model (`EnvoxyBase`)
* `alembic/versions/0001_create_product.py` – initial migration
* `Makefile` – thin targets wrapping the `envoxy-alembic` CLI

Environment variable `SERVICE_MODELS` is used by the Alembic `env.py` logic
to locate your aggregated models module.

Common commands:
```
SERVICE_MODELS=examples.template_service.models envoxy-alembic revision -m "add field" --autogenerate
SERVICE_MODELS=examples.template_service.models envoxy-alembic upgrade head
SERVICE_MODELS=examples.template_service.models envoxy-alembic current
```

Or via Make targets (already exporting `SERVICE_MODELS`):
```
make alembic-rev m="add field"
make alembic-upgrade
make alembic-current
```
