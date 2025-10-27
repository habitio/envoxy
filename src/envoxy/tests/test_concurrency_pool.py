# ruff: noqa: F401,F841
import threading
import time

from envoxy.postgresql.client import SemaphoreThreadedConnectionPool, Client


class DummyConn:
    def cursor(self):
        class Ctx:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
            def execute(self, *args, **kwargs):
                return None
        return Ctx()
    def close(self):
        return None


def test_semaphore_limits_and_timeouts():
    max_conn = 3

    pool = SemaphoreThreadedConnectionPool(1, max_conn, host='localhost', port=5432, dbname='db', user='u', password='p')

    # monkeypatch internals: directly insert dummy connections into the internal pool
    conns = [DummyConn() for _ in range(max_conn)]
    for c in conns:
        pool.putconn(c)

    acquired = []
    lock = threading.Lock()

    def worker(i):
        try:
            conn = pool.getconn(timeout=1)
        except Exception as e:
            with lock:
                acquired.append(('timeout', i))
            return
        with lock:
            acquired.append(('ok', i))
        # hold the connection a little while
        time.sleep(0.2)
        pool.putconn(conn)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # assert that at least one thread hit timeout since 6 > max_conn and hold time
    assert any(s == 'timeout' for s, _ in acquired)
