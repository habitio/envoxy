"""Example SQLAlchemy models for a consumer module using Envoxy framework.

This file demonstrates a recommended model structure and how to register the
Envoxy listeners (so id/created/updated/href are auto-populated).
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Index
from sqlalchemy.orm import declarative_base

from envoxy.db.envoxy_mixin import EnvoxyMixin, register_envoxy_listeners

Base = declarative_base()


class Product(EnvoxyMixin, Base):
    # consumer projects use plural table names by convention
    __tablename__ = "products"

    # EnvoxyMixin provides: id (String(36)), created, updated, href
    sku = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    metadata = Column(JSON, nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_product_sku", "sku"),
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
