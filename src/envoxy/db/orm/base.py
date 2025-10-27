from sqlalchemy.orm.decl_api import declarative_base
from .mixin import EnvoxyMixin
from .meta import EnvoxyMeta

# Create a declarative base that uses EnvoxyMeta as its metaclass so naming
# rules are applied by SQLAlchemy's machinery without metaclass conflicts.
_DeclarativeBase = declarative_base(metaclass=EnvoxyMeta)


class EnvoxyBase(EnvoxyMixin, _DeclarativeBase):
    """
    EnvoxyBase is an abstract base class for ORM models in the Envoxy project.

    This class inherits from EnvoxyMixin and _DeclarativeBase, providing shared
    functionality and declarative mapping for all derived ORM models. It is marked
    as abstract and should not be instantiated directly.

    Attributes:
        __abstract__ (bool): Indicates that this class is abstract and should not
            be mapped to a database table.
    """

    __abstract__ = True
