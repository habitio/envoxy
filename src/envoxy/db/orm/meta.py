import inflect
from sqlalchemy.orm.decl_api import DeclarativeMeta
from .constants import AUX_TABLE_PREFIX


class EnvoxyMeta(DeclarativeMeta):
    """Metaclass to enforce 'aux_' prefix and plural table names for SQLAlchemy tables.

    Inherit from SQLAlchemy's `DeclarativeMeta` so `EnvoxyBase = EnvoxyMixin +
    declarative_base()` composes cleanly without metaclass conflicts.
    """

    _inflector = inflect.engine()

    def __init__(cls, name, bases, dct):
        # If this class is an abstract sentinel (like the mixin or an
        # intentionally abstract declarative base), skip naming.
        if name == "EnvoxyMixin" or dct.get("__abstract__", False):
            # Let SQLAlchemy continue setup for abstract bases.
            super().__init__(name, bases, dct)
            return

        # Compute table name early so SQLAlchemy sees it during mapping.
        prefix = AUX_TABLE_PREFIX
        exception_tablename = dct.get("__exception_tablename__") or getattr(
            cls, "__exception_tablename__", None
        )
        if exception_tablename:
            tablename = exception_tablename
        else:
            explicit_tablename = dct.get("__tablename__") or getattr(
                cls, "__tablename__", None
            )
            if explicit_tablename:
                base = explicit_tablename
            else:
                # Prefer the concrete class name for pluralization.
                base = getattr(cls, "__name__", name)
            base = base.split(".")[-1]
            tablename = type(cls)._inflector.plural(base)

        tablename = tablename.lower()
        if not tablename.startswith(prefix):
            tablename = prefix + tablename

        # Assign the computed table name before invoking SQLAlchemy's
        # DeclarativeMeta so the mapping sees the correct __tablename__.
        cls.__tablename__ = tablename

        # Now let SQLAlchemy perform its usual declarative setup.
        super().__init__(name, bases, dct)
