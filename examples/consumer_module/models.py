"""Example SQLAlchemy models for a consumer module using Envoxy framework.

This file demonstrates a recommended model structure and how to register the
Envoxy listeners (so id/created/updated/href are auto-populated).
"""
from sqlalchemy import Column, String, Integer, JSON, Index

from envoxy.db.orm.base import EnvoxyBase, register_envoxy_listeners


class Product(EnvoxyBase):
    # EnvoxyMixin provides: id (String(36)), created, updated, href
    sku = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    metadata = Column(JSON, nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_products_sku", "sku"),
    )


# Application startup helper
def init_models():
    """Call this from the application that consumes the framework.

    Example:
        from examples.consumer_module.models import init_models
        init_models()
    """
    # register the envoxy listeners - call this once after models are imported
    register_envoxy_listeners()
