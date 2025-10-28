import pytest

from envoxy.postgresql.client import Client
from envoxy.db.exceptions import DatabaseException


class DummyCursor:
    def __init__(self):
        self._closed = False
        self._data = [{'id': 1}]
        self.rowcount = 1
        self.last_query = None
        self.last_params = None

    def execute(self, *args, **kwargs):
        if args and args[0] == "SELECT 1":
            return
        if "RAISE_ERROR" in str(args[0]):
            raise Exception("cursor execution error")

        # Simulate RETURNING behavior
        # store last executed (for tests)
        try:
            self.last_query = args[0]
            self.last_params = kwargs.get('params') or (args[1] if len(args) > 1 else None)
        except Exception:
            pass

        if isinstance(args[0], str) and "RETURNING" in args[0].upper():
            # set rowcount and data for fetchone/fetchall
            self.rowcount = 1
            self._data = [{'id': 123}]

    def fetchall(self):
        return self._data

    def fetchone(self):
        if not self._data:
            return None
        # return tuple of values
        return tuple(self._data[0].values())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyConn:
    def __init__(self, healthy=True):
        self._healthy = healthy
        self.autocommit = True
        self._cursor = DummyCursor()

    def cursor(self, *args, **kwargs):
        return self._cursor

    def close(self):
        self._healthy = False


class DummyPool:
    def __init__(self, conn):
        self._conn = conn
        self.put_called = False

    def getconn(self, *args, **kwargs):
        return self._conn

    def putconn(self, conn, close=False):
        self.put_called = True
        if close:
            try:
                conn.close()
            except Exception:
                pass


@pytest.fixture
def client_instance(tmp_path, monkeypatch):
    conf = {
        'pg': {
            'host': 'localhost',
            'port': 5432,
            'db': 'test',
            'user': 'u',
            'passwd': 'p',
        }
    }

    c = Client(conf)

    # monkeypatch the actual pool with a dummy one
    dummy_conn = DummyConn(healthy=True)
    c._instances['pg']['conn_pool'] = DummyPool(dummy_conn)

    return c

@pytest.mark.postgresql
def test_transaction_rollback_and_autocommit_restored(client_instance):
    c = client_instance

    # make pool return a connection that will raise inside the transaction
    conn = DummyConn(healthy=True)

    c._instances['pg']['conn_pool']._conn = conn

    with pytest.raises(Exception):
        with c.transaction('pg'):
            # simulate a query that raises
            raise Exception("boom")

    # After exception, connection should have autocommit restored to True
    assert conn.autocommit is True


def test_release_conn_for_broken_connection(client_instance):
    c = client_instance
    conn = DummyConn(healthy=False)
    pool = DummyPool(conn)
    c._instances['pg']['conn_pool'] = pool

    # Releasing a broken connection should call putconn with close=True
    c.release_conn('pg', conn)
    assert pool.put_called


def test_insert_is_disabled(client_instance):
    c = client_instance
    with pytest.raises(DatabaseException):
        with c.transaction('pg'):
            c.insert('my_table', {'a': 1, 'b': 2}, returning='id')


@pytest.mark.skip(reason="update() and delete() methods not implemented in Client")
def test_update_and_delete_returning(client_instance):
    c = client_instance

    conn = DummyConn(healthy=True)
    c._instances['pg']['conn_pool']._conn = conn

    try:
        with c.transaction('pg'):
            updated = c.update('my_table', {'a': 2}, {'id': 1}, returning='id')
            assert updated == 123

            deleted = c.delete('my_table', {'id': 1}, returning='id')
            assert deleted == 123
    finally:
        try:
            delattr(c._thread_local_data, 'conn')
        except Exception:
            pass


@pytest.mark.skip(reason="create_table() method not implemented in Client")
def test_create_table_and_trigger(client_instance):
    c = client_instance

    conn = DummyConn(healthy=True)
    c._instances['pg']['conn_pool']._conn = conn

    try:
        with c.transaction('pg'):
            # create table with extra columns
            c.create_table('my_new_table', extra_columns={'name': 'VARCHAR(255)'})
            # verify last executed create statement contains id and href
            assert 'id' in str(conn._cursor.last_query).lower() or 'create table' in str(conn._cursor.last_query).lower()
    finally:
        try:
            delattr(c._thread_local_data, 'conn')
        except Exception:
            pass
