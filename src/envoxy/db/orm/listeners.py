# ruff: noqa: F401
import uuid
import datetime
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.orm.decl_api import registry
from sqlalchemy import event

from .mixin import EnvoxyMixin
from .base import EnvoxyBase

def _now_utc():
    return datetime.datetime.now(datetime.timezone.utc)

def _entity_from_mapper(mapper: Mapper, target) -> str:
    try:
        _tbl = getattr(mapper.local_table, 'name', None)
        if not _tbl:
            raise AttributeError
    except Exception:
        _tbl = getattr(target, '__tablename__', None) or mapper.class_.__name__.lower()
    return _tbl.split('.')[-1]

def _before_insert(mapper, connection, target):
    if not getattr(target, 'id', None):
        target.id = str(uuid.uuid4())
    now = _now_utc()
    if not getattr(target, 'created', None):
        target.created = now
    target.updated = now
    if not getattr(target, 'href', None):
        entity = _entity_from_mapper(mapper, target)
        target.href = f"/v3/data-layer/{entity}/{target.id}"

def _before_update(mapper, connection, target):
    target.updated = _now_utc()

def register_envoxy_listeners():
    """Register ORM listeners for all mapped classes that use EnvoxyMixin."""
    # idempotency guard - don't register listeners more than once
    if getattr(register_envoxy_listeners, '_registered', False):
        return
    def mapper_configured(mapper, class_):
        # Enforce that every mapped class inherits from EnvoxyBase.
        # This prevents accidental mappings that bypass the thin-layer base.
        if not issubclass(class_, EnvoxyBase):
            raise RuntimeError(
                f"Mapped class {class_.__module__}.{class_.__name__} must inherit from EnvoxyBase"
            )

        # Attach listeners that populate id/created/updated/href.
        if issubclass(class_, EnvoxyMixin):
            event.listen(mapper, 'before_insert', _before_insert)
            event.listen(mapper, 'before_update', _before_update)
    # Attach to the Mapper class-level event so it fires for all mappers.
    from sqlalchemy.orm.mapper import Mapper as _MapperClass
    event.listen(_MapperClass, 'mapper_configured', mapper_configured)
    register_envoxy_listeners._registered = True
