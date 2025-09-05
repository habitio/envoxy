from envoxy.db.orm.schema import Column, Index
from envoxy.db.orm.sqltypes import String, Integer, JSON
from envoxy.db.orm.base import EnvoxyBase


class Product(EnvoxyBase):
    sku = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    cdata = Column(JSON, nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_products_sku", "sku"),
    )
