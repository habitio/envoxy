"""Query examples for the template service.

Contains short, copy-paste ready snippets demonstrating common patterns:
- ORM selects, inserts, updates and deletes
- Raw SQL via SQLAlchemy Core with `to_sa_text` compatibility helper
- Transactional decorator and context-manager use
- Mixing Core and ORM in one transaction

These examples assume the service exposes `examples.template_service.models`
and that `envoxy` is installed in the running environment.
"""

from examples.template_service.models import Product
from envoxy import pgsqlc
from envoxy.db.helpers import to_sa_text


def orm_get_by_sku(server_key: str, sku: str):
    """Return Product by SKU using the server_key-first session helper."""
    with pgsqlc.sa_session(server_key) as session:
        return session.query(Product).filter(Product.sku == sku).first()


def orm_create(server_key: str, sku: str, name: str, price_cents: int, metadata=None):
    """Create and persist a Product using only a server_key."""
    p = Product(sku=sku, name=name, price_cents=price_cents)
    with pgsqlc.sa_session(server_key) as session:
        session.add(p)
        # commit occurs on context exit
        return p


def orm_update_price(server_key: str, product_id: str, new_price: int):
    with pgsqlc.sa_session(server_key) as session:
        p = session.get(Product, product_id)
        if not p:
            return None
        p.price_cents = new_price
        return p


def orm_delete(server_key: str, product_id: str):
    with pgsqlc.sa_session(server_key) as session:
        p = session.get(Product, product_id)
        if not p:
            return False
        session.delete(p)
        return True


# Raw SQL examples
def raw_select_by_sku(server_key: str, sku: str):
    mgr = pgsqlc.sa_manager(server_key)
    sql = to_sa_text("SELECT id, sku, name, price_cents, href FROM products WHERE sku = %(sku)s")
    with mgr.engine.connect() as conn:
        res = conn.execute(sql, {"sku": sku})
        return res.mappings().all()


def raw_insert_product(server_key: str, sku: str, name: str, price_cents: int):
    mgr = pgsqlc.sa_manager(server_key)
    sql = to_sa_text(
        "INSERT INTO products (id, sku, name, price_cents) VALUES (%(id)s, %(sku)s, %(name)s, %(price_cents)s)"
    )
    params = {"id": None, "sku": sku, "name": name, "price_cents": price_cents}
    # Use engine.begin() to ensure transactional insert
    with mgr.engine.begin() as conn:
        conn.execute(sql, params)


# Transactional decorator example (server_key-first)
# NOTE: do NOT apply the decorator at module import time without a configured
# default server (it calls `get_default_server_key()` during decoration).
# Instead, create the decorated function at runtime or explicitly pass the
# server_key to the decorator.

def make_find_or_create_for_server(server_key: str):
    """Return a `find_or_create` function decorated for the given server_key.

    Usage:
        fn = make_find_or_create_for_server('primary')
        fn(sku='X', name='Y')
    """

    @pgsqlc.sa_transactional(server_key)
    def _find_or_create(session=None, sku: str | None = None, name: str | None = None):
        p = session.query(Product).filter_by(sku=sku).first()
        if p:
            return p
        p = Product(sku=sku, name=name, price_cents=0)
        session.add(p)
        return p

    return _find_or_create


def mixed_core_orm_transaction(server_key: str, sku: str):
    """Demonstrate using Core + ORM in one transaction on the same connection."""
    mgr = pgsqlc.sa_manager(server_key)
    with mgr.engine.begin() as conn:
        # create a session bound to the connection
        from sqlalchemy.orm import Session

        with Session(bind=conn) as session:
            p = session.query(Product).filter_by(sku=sku).first()
            count = conn.execute(to_sa_text("SELECT count(*) FROM products WHERE sku = %(sku)s"), {"sku": sku}).scalar()
            return p, count
