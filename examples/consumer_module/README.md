Example consumer module

This minimal example shows how a module using the Envoxy framework should
declare models and register the Envoxy listeners.

Steps to use in a real app:

1. Add this package (or similar) to your project.
2. Import and call `init_models()` during application startup (after your
     application's configuration is available and models are imported). By
     convention consumer projects use plural table names (e.g. `products`).
3. Use Envoxy's small, server_key-first helpers so developers only choose a
     `server_key`. Examples live in `queries.py`. Key helpers (preferred usage):

     - `from envoxy import pgsqlc`
         - `with pgsqlc.session('primary') as session: ...` commits on success and
             rolls back on error. The sessionmaker is configured with
             `expire_on_commit=False` so objects remain usable after commit.
     - `from envoxy import pgsqlc`
         - `@pgsqlc.transactional('primary')` runs the wrapped function in a
             managed transaction and injects a `session` kwarg into the function
             (the decorated function should accept `session=None`).

     - `pgsqlc.manager('primary')` returns the manager/engine object when you
         need raw connections or Core-level operations.

     If you have existing SQL written with psycopg2-style placeholders
     (`%(name)s`), use `envoxy.db.helpers.to_sa_text()` to convert it to a
     SQLAlchemy `text()` object using `:name` bind parameters. Prefer writing
     queries with `:name` directly for new code.

     Envoxy reads database servers from `Config.get('psql_servers')`. Wire the
     config at bootstrap, for example:

     ```py
     from envoxy.utils.config import Config
     Config.set_file_path('dev_conf.json')
     ```

Examples
--------
This package includes `queries.py` with copy-pasteable examples showing:
- ORM queries (select, insert, update) using `pgsqlc.session(server_key)`
- Raw SQL via SQLAlchemy Core/text using `pgsqlc.manager(server_key)` and
    `to_sa_text()` for compatibility with `%(name)s` placeholders
- Mixing ORM and Core in a single transaction by binding a Session to the
    same Engine connection

Use `queries.py` as a starting point for consumer modules that need both the
convenience of the ORM and the performance/flexibility of raw SQL when needed.

This package is only a demonstration — consumer projects should declare their
own models under their app's package.
