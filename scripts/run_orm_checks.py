#!/usr/bin/env python3
"""Run quick ORM naming and listener checks without pytest."""
import datetime
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure repository root is on sys.path so example packages are importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from envoxy.db.orm import register_envoxy_listeners, EnvoxyBase
from examples.consumer_module.models import Product


def main():
    register_envoxy_listeners()
    engine = create_engine('sqlite:///:memory:')
    EnvoxyBase.metadata.create_all(engine)

    print('tablename:', Product.__tablename__)
    assert Product.__tablename__ == 'aux_products'

    idx_names = [i.name for i in Product.__table__.indexes]
    print('indexes:', idx_names)
    assert any(name.startswith('aux_') for name in idx_names)

    Session = sessionmaker(bind=engine)
    s = Session()
    p = Product(sku='SKU1', name='Test', price_cents=100)
    s.add(p)
    s.commit()

    print('id:', p.id)
    print('href:', p.href)
    print('created:', p.created)
    print('updated:', p.updated)

    assert p.id is not None
    assert p.href.startswith('/v3/data-layer/')
    assert isinstance(p.created, datetime.datetime)
    assert isinstance(p.updated, datetime.datetime)

    print('ORM checks passed')


if __name__ == '__main__':
    main()
