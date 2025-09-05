# Migrations How-To

Envoxy ships a packaged Alembic setup and CLI (`envoxy-alembic`).

## Create Migration
```
envoxy-alembic revision -m "add product" --autogenerate
```

## Apply
```
envoxy-alembic upgrade head
```

## Current / History
```
envoxy-alembic current
envoxy-alembic history --verbose
```

## Model Discovery
Alembic `env.py` tries to import your service models automatically. Ensure your models module imports (or defines) all `EnvoxyBase` subclasses so `EnvoxyBase.metadata` is populated.

## SQLite Relative Paths
Relative SQLite URLs are converted to absolute filesystem paths; directories are created if missing.

## CI Check
```
python -m envoxy.tools.check_migrations path/to/versions
```
Exit codes:
- 0 ok
- 2 directory missing
- 3 no migration files

## Regenerating After Changes
Edit models -> re-run `revision --autogenerate` -> inspect diff carefully (naming & audit columns are automatic).

## Downgrades
Use with caution; default flow emphasises forward migrations. Provide explicit downgrade logic only when necessary.
