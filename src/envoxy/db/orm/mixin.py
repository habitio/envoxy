from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql.schema import Index
from .constants import AUX_TABLE_PREFIX

class EnvoxyMixin:
    # Prevent SQLAlchemy from mapping this mixin as a concrete table.
    __abstract__ = True
    id = Column('id', String(36), primary_key=True)
    created = Column('created', DateTime, nullable=False)
    updated = Column('updated', DateTime, nullable=False)
    href = Column('href', String(1024), nullable=False)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Enforce aux_ prefix for all Index names in __table_args__
        table_args = getattr(cls, "__table_args__", None)
        if table_args:
            new_args = []
            for arg in table_args:
                if isinstance(arg, Index):
                    name = getattr(arg, 'name', None)
                    # Ensure name is a string before calling startswith.
                    if not (isinstance(name, str) and name):
                        # If name is missing or not a string, generate a safe
                        # name using the index expressions. Fall back to
                        # a generic name prefixed with the configured prefix.
                        safe_name = AUX_TABLE_PREFIX + 'index'
                        kwargs = {}
                        if getattr(arg, 'unique', False):
                            kwargs['unique'] = True
                        new_args.append(Index(safe_name, *arg.expressions, **kwargs))
                    else:
                        if not name.startswith(AUX_TABLE_PREFIX):
                            # Recreate Index with aux_ prefix
                            kwargs = {}
                            if getattr(arg, 'unique', False):
                                kwargs['unique'] = True
                            new_args.append(Index(AUX_TABLE_PREFIX + name, *arg.expressions, **kwargs))
                        else:
                            new_args.append(arg)
                else:
                    new_args.append(arg)
            cls.__table_args__ = tuple(new_args)
