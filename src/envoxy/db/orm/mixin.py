from sqlalchemy import Column, String, DateTime
from .meta import EnvoxyMeta


from sqlalchemy import Index

class EnvoxyMixin(metaclass=EnvoxyMeta):
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
                    name = arg.name
                    if not name.startswith("aux_"):
                        # Recreate Index with aux_ prefix
                        new_args.append(Index("aux_" + name, *arg.expressions, **arg.kwargs))
                    else:
                        new_args.append(arg)
                else:
                    new_args.append(arg)
            cls.__table_args__ = tuple(new_args)
