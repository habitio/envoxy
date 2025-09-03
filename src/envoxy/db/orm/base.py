from sqlalchemy.orm import declarative_base
from .mixin import EnvoxyMixin

class EnvoxyBase(EnvoxyMixin, declarative_base()):
    pass
