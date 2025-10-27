import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from envoxy.db.orm import register_envoxy_listeners, EnvoxyBase
from examples.consumer_module.models import Product


def test_table_and_index_naming_and_listeners():
    # Ensure listeners are registered (idempotent)
    register_envoxy_listeners()

    # In-memory SQLite for fast tests
    engine = create_engine("sqlite:///:memory:")
    # Create tables for the example models
    EnvoxyBase.metadata.create_all(engine)

    # Check table name enforced
    assert Product.__tablename__.startswith("aux_")
    assert Product.__tablename__ == "aux_products"

    # Index names should be prefixed
    idx_names = [i.name for i in Product.__table__.indexes]
    assert any(name.startswith("aux_") for name in idx_names)

    # Use a real session to trigger before_insert/before_update listeners
    Session = sessionmaker(bind=engine)
    session = Session()

    p = Product(sku="SKU1", name="Test", price_cents=100)
    session.add(p)
    session.commit()

    # After flush/commit the listeners should have populated these fields
    assert getattr(p, "id", None) is not None
    assert getattr(p, "href", "").startswith("/v3/data-layer/")
    assert isinstance(getattr(p, "created"), datetime.datetime)
    assert isinstance(getattr(p, "updated"), datetime.datetime)
