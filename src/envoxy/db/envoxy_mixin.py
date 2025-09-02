"""Envoxy SQLAlchemy mixin and event listeners.

Provide EnvoxyMixin that declares id/created/updated/href columns and
listeners to populate them in Python before insert/update.

Usage:
 - Import EnvoxyMixin and inherit your declarative models from it.
 - Call `register_envoxy_listeners()` early in your application (after models are defined).
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import Mapper
from sqlalchemy import event
import uuid
import datetime


class EnvoxyMixin:
    """Mixin that declares the required envoxy columns.

    Notes:
      - types mirror the JSON definitions used across the data-layer (varchar(36), timestamp w/o tz).
      - application code will populate the values (listeners below).
    """

    id = Column('id', String(36), primary_key=True)
    created = Column('created', DateTime, nullable=False)
    updated = Column('updated', DateTime, nullable=False)
    href = Column('href', String(1024), nullable=False)


def _now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def _entity_from_mapper(mapper: Mapper, target) -> str:
    # Prefer explicit __tablename__ on class; strip schema if present
    try:
        tbl = mapper.local_table.name
    except Exception:
        tbl = getattr(target, '__tablename__', None) or mapper.class_.__name__.lower()
    return tbl.split('.')[-1]


def _before_insert(mapper, connection, target):
    # Populate id, created, updated, href if missing
    if not getattr(target, 'id', None):
        target.id = str(uuid.uuid4())

    now = _now_utc()
    if not getattr(target, 'created', None):
        target.created = now
    # always set updated
    target.updated = now

    if not getattr(target, 'href', None):
        entity = _entity_from_mapper(mapper, target)
        target.href = f"/v3/data-layer/{entity}/{target.id}"


def _before_update(mapper, connection, target):
    # update updated timestamp
    target.updated = _now_utc()


def register_envoxy_listeners():
    """Register ORM listeners for all mapped classes that use EnvoxyMixin.

    Call after your models have been defined/mapped (e.g., after import).
    """
    from sqlalchemy.orm import class_mapper, registry

    # Attach listeners to mapper configuration time: when a mapper is configured,
    # if it inherits EnvoxyMixin then attach listeners for that mapper.
    def mapper_configured(mapper, class_):
        if issubclass(class_, EnvoxyMixin):
            event.listen(mapper, 'before_insert', _before_insert)
            event.listen(mapper, 'before_update', _before_update)

    event.listen(registry(), 'mapper_configured', mapper_configured)
