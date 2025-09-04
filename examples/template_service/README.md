Template service example

This example shows the minimal layout a pyservice should use so it can run
the framework-provided Alembic configuration shipped inside the `envoxy`
package without duplicating `alembic.ini` or `env.py`.

Pattern:
- `template_service/models.py` — aggregator that imports models, exposes
  `metadata` and registers listeners.
- `scripts/alembic.sh` — small wrapper that sets `PYTHONPATH`, `SERVICE_MODELS`
  and runs `python -m alembic -c <envoxy-alembic.ini> ...` so migrations run
  in the service virtualenv.
- `Makefile` — convenience targets for common alembic commands.

Copy the layout below into your service and adjust the package name.
