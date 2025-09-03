import inflect

class EnvoxyMeta(type):
    """Metaclass to enforce 'aux_' prefix and plural table names for SQLAlchemy tables, with opt-out via __exception_tablename__."""
    _inflector = inflect.engine()
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        if name != "EnvoxyMixin":
            prefix = "aux_"
            exception_tablename = getattr(cls, "__exception_tablename__", None)
            if exception_tablename:
                tablename = exception_tablename
            else:
                tablename = getattr(cls, "__tablename__", None) or name
                tablename = type(cls)._inflector.plural(tablename)
            tablename = tablename.lower()
            if not tablename.startswith(prefix):
                tablename = prefix + tablename
            cls.__tablename__ = tablename
