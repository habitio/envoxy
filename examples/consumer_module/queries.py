"""Query examples for a consumer module using Envoxy models.

These examples show common patterns using SQLAlchemy ORM and (when needed)
SQLAlchemy Core/text while using Envoxy's dispatcher helpers exported as
``pgsqlc`` from the package root (``from envoxy import pgsqlc``).

Key points:
- Use ``pgsqlc.session(server_key)`` to obtain a context-managed SQLAlchemy
    Session; it commits on success and rolls back on exception.
- Use ``pgsqlc.sa_manager(server_key)`` to access the underlying manager/Engine
    when you need raw connections or high-performance Core operations.
- Existing SQL written with psycopg2-style named placeholders ``%(name)s`` can
    be converted with ``envoxy.db.helpers.to_sa_text`` (converts to ``:name``)
    as a compatibility step. Prefer writing queries with ``:name`` directly.

These snippets are intended for copy/paste into consumer modules. They
assume your app has bootstrapped configuration (``Config.set_file_path``) and
configured ``psql_servers`` so ``pgsqlc.manager``/``pgsqlc.session`` can
resolve a server_key.
"""

from examples.consumer_module.models import Product

# Import the dispatcher exported at package root so consumer modules can keep
# the same surface as before: `from envoxy import pgsqlc`.
from envoxy import pgsqlc
from envoxy.db.helpers import to_sa_text

# Use the dispatcher helpers (server_key-first):
# - `pgsqlc.session(server_key)` returns a context manager that yields a
#   SQLAlchemy Session and handles commit/rollback for you.
# - `pgsqlc.manager(server_key)` returns the Envoxy session/engine manager
#   exposing `.engine` for Core-level operations.
# - `pgsqlc.transactional(server_key)` returns a decorator that runs the
#   wrapped function inside a managed transaction and injects a `session`
#   kwarg (i.e. the wrapped function should accept `session=None`).
# If you need custom Engines for advanced scenarios you can still create an
# EnvoxySessionManager directly; these examples prefer the server_key helpers.


# ORM: simple select
def orm_select_by_sku(server_key: str, sku: str):
    """Return a Product by SKU using Envoxy's server_key-first session API.

    The function accepts only the ``server_key`` (the consumer picks this from
    their config). ``pgsqlc.session(server_key)`` yields a SQLAlchemy Session;
    the context manager commits on successful exit and rolls back on
    exceptions. Returned ORM objects remain usable after commit because
    Envoxy configures the sessionmaker with ``expire_on_commit=False``.
    """

    with pgsqlc.sa_session(server_key) as _session:
        return _session.query(Product).filter(Product.sku == sku).first()


# ORM: create/insert
def orm_create_product(server_key: str, sku: str, name: str, price_cents: int, metadata=None):
    """Create and persist a Product using only a ``server_key``.

    The context manager will commit on success. The created ORM instance will
    still have its attributes available after commit because Envoxy sets
    ``expire_on_commit=False`` on the sessionmaker.
    """
    _p = Product(sku=sku, name=name, price_cents=price_cents, metadata=metadata)
    with pgsqlc.sa_session(server_key) as _session:
        _session.add(p)
        # session_scope commits on successful exit; returned object remains
        # usable because Envoxy's sessionmaker sets expire_on_commit=False.
        return _p


# ORM: update
def orm_update_price(server_key: str, product_id: str, new_price: int):
    """Update a product's price using only the ``server_key``.

    Uses the server_key-first session helper so callers don't manage
    session/transactions directly. The session commits on exit.
    """
    with pgsqlc.sa_session(server_key) as session:
        p = session.get(Product, product_id)
        if not p:
            return None
        p.price_cents = new_price
        # session_scope will commit on exit
        return p


# Core / raw SQL: execute a raw SELECT with parameters
def raw_select_by_sku(server_key: str, sku: str):
    """Run a raw SQL SELECT via SQLAlchemy Core and return mapping rows.

    Use this when you need low-level SQL (complex joins, window functions,
    planner hints, etc.). If your SQL uses psycopg2-style ``%(name)s``
    placeholders, convert it with ``to_sa_text`` which produces a
    SQLAlchemy ``text()`` object using ``:name`` bind parameters. The
    returned rows are dict-like mappings accessible as normal dicts.
    """
    _mgr = pgsqlc.sa_manager(server_key)
    _sql = to_sa_text("SELECT id, sku, name, price_cents, href FROM products WHERE sku = %(sku)s")
    with _mgr.engine.connect() as _conn:
        _result = _conn.execute(_sql, {"sku": sku})
        _rows = _result.mappings().all()
    return _rows

# Transaction example: mix ORM + Core inside a single transaction
def mixed_transaction_example(server_key: str, sku: str, extra_debug=False):
    """Run Core and ORM work in a single DB transaction.

    Opens a connection with ``mgr.engine.begin()`` (a transactional context)
    and creates an ORM ``Session`` bound to that same connection so both
    Core and ORM statements participate in the same transaction.
    """
    # Bind the session to the same connection via begin() context
    _mgr = pgsqlc.sa_manager(server_key)
    with _mgr.engine.begin() as _connection:
        # Option A: use ORM session tied to the connection
        from sqlalchemy.orm import Session # Just an example that is possible to use Session directly
        with Session(bind=_connection) as _sess:
            _prod = _sess.query(Product).filter_by(sku=sku).first()
            if extra_debug:
                print('found', _prod)
            # run a raw count using the same connection
            _count = _connection.execute(to_sa_text("SELECT count(*) FROM products WHERE sku = %(sku)s"), {"sku": sku}).scalar()
            if extra_debug:
                print('count', _count)
            return _prod, _count


# Note: these examples assume your application has bootstrapped Envoxy
# configuration (for example `Config.set_file_path(...)`) and configured
# `psql_servers`. The examples use Envoxy's dispatcher helpers (``pgsqlc``)
# to obtain managers/sessions by server_key so consumers do not need to create
# engines manually.


# ------------------------
# Envoxy session manager examples (server_key-first)
# ------------------------

def example_using_server_key(server_key: str = None):
    """Show a few simple ways to use the server_key helpers exported by
    Envoxy. If ``server_key`` is omitted, `pgsqlc.sa_manager`/`pgsqlc.sa_session`
    will use the configured default server key.

    Demonstrates:
    - context-manager style via ``pgsqlc.sa_session(server_key)``
    - decorator style via ``@pgsqlc.sa_transactional(server_key)`` which injects
      a ``session`` kwarg into the wrapped function
    """

    # context manager style — commits on success, rolls back on error
    with pgsqlc.sa_session(server_key) as _session:
        _ = _session.query(Product).filter_by(sku="SKX").first()

    # decorator style — the decorated function must accept `session=None`
    @pgsqlc.sa_transactional(server_key)
    def find_or_create(sku: str, session=None):
        # `session` is injected by the decorator as a kwarg
        _prod = session.query(Product).filter_by(sku=sku).first()
        if _prod:
            return _prod
        _prod = Product(sku=sku, name="Auto", price_cents=0)
        session.add(_prod)
        return _prod

    # call helpers implemented above that accept server_key
    _created = orm_create_product(server_key, "SKX", "Example", 100)
    _found = orm_select_by_sku(server_key, "SKX")
    _updated = orm_update_price(server_key, created.id, 200)
    # or use decorator example
    _new = find_or_create("SKX")

    return _created, _found, _updated, _new
