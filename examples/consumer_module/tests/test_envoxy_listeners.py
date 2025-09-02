import re
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from examples.consumer_module.models import Product, init_models, Base


def test_envoxy_listeners_populate_fields():
    # Initialize listeners (registers before_insert / before_update hooks)
    init_models()

    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    p = Product(sku="SKU-123", name="Test product", price_cents=199)
    session.add(p)
    session.commit()

    # After commit the listeners should have populated id, created, updated, href
    assert getattr(p, "id", None) is not None
    assert isinstance(p.id, str)
    assert len(p.id) == 36

    assert getattr(p, "created", None) is not None
    assert getattr(p, "updated", None) is not None
    assert isinstance(p.created, datetime)
    assert isinstance(p.updated, datetime)
    assert p.updated >= p.created

    # href follows pattern /v3/data-layer/<entity>/<uuid>
    href = getattr(p, "href", None)
    assert href is not None
    m = re.match(r"^/v3/data-layer/[A-Za-z0-9_\-]+/[0-9a-fA-F\-]{36}$", href)
    assert m is not None

    session.close()
