"""Models aggregator for the template example service.

This file imports model modules (side-effect: SQLAlchemy mappings are
registered), exposes `metadata` and registers the Envoxy listeners.
Keep imports here minimal to avoid pulling heavy runtime code.
"""
from envoxy.db.orm.base import EnvoxyBase
from envoxy.db.orm import register_envoxy_listeners

# Import your model modules here. Example placeholder:
from .product import Product

# Expose metadata for Alembic discovery
metadata = EnvoxyBase.metadata

# Register idempotent listeners
register_envoxy_listeners()
