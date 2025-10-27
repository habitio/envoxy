from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from envoxy.db.envoxy_mixin import EnvoxyMixin, register_envoxy_listeners


Base = declarative_base()


class MyModel(EnvoxyMixin, Base):
    __tablename__ = 'mymodel'
    pk = Column(Integer, primary_key=True)


def test_listeners_populate_fields():
    register_envoxy_listeners()
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()

    m = MyModel()
    s.add(m)
    s.commit()

    assert m.id is not None
    assert isinstance(m.id, str)
    assert m.created is not None
    assert m.updated is not None
    assert m.href.endswith('/' + m.id)

    # update and check updated changes
    prev = m.updated
    m.pk = 1
    s.add(m)
    s.commit()
    assert m.updated >= prev
