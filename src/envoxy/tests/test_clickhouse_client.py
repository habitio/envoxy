# ruff: noqa: F401,F821
"""
Unit tests for the ClickHouse client (envoxy.clickhouse.client).

All tests are fully isolated — no real ClickHouse connection is required.
External calls to ``clickhouse_connect.get_client`` are monkeypatched with
lightweight fakes that cover the expected contract.
"""

import decimal
import uuid
from datetime import date, datetime, timezone
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest

from envoxy.clickhouse.client import (
    Client,
    _normalize_row,
    _normalize_value,
)
from envoxy.db.exceptions import DatabaseException


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------

def _make_query_result(columns: tuple, rows: list[tuple]):
    """Build a minimal fake ``QueryResult`` returned by clickhouse_connect."""
    result = MagicMock()
    result.column_names = columns
    result.result_rows = rows
    return result


class FakeChClient:
    """Minimal fake of ``clickhouse_connect.Client``."""

    def __init__(self, rows=None, columns=None, raise_on_query=None, ping_ok=True):
        self._rows = rows or [(1,)]
        self._columns = columns or ("count",)
        self._raise_on_query = raise_on_query
        self._ping_ok = ping_ok
        self.close_called = False
        self.queries: list[tuple] = []   # (sql, parameters, settings)

    def ping(self) -> bool:
        return self._ping_ok

    def query(self, sql, parameters=None, settings=None):
        self.queries.append((sql, parameters, settings))
        if self._raise_on_query:
            raise self._raise_on_query
        return _make_query_result(self._columns, self._rows)

    def close(self):
        self.close_called = True


@pytest.fixture(autouse=True)
def reset_client_singleton():
    """Reset the Client singleton between tests to ensure isolation."""
    original = Client._instance
    Client._instance = None
    yield
    Client._instance = original


@pytest.fixture
def fake_ch_client():
    return FakeChClient(rows=[(42,)], columns=("count",))


@pytest.fixture
def client_instance(fake_ch_client, monkeypatch):
    """Return a Client wired to a FakeChClient, bypassing real TCP connections."""
    conf = {
        "analytics": {
            "host": "localhost",
            "port": 8123,
            "db": "raw",
            "username": "default",
            "passwd": "",
        }
    }

    with patch("envoxy.clickhouse.client.clickhouse_connect") as mock_cc:
        mock_cc.get_client.return_value = fake_ch_client
        c = Client(conf)

    # Inject the fake directly so later calls don't re-create it.
    c._instances["analytics"]["ch_client"] = fake_ch_client
    return c, fake_ch_client


# ---------------------------------------------------------------------------
# _normalize_value
# ---------------------------------------------------------------------------

class TestNormalizeValue:

    def test_datetime_naive_becomes_utc_string(self):
        dt = datetime(2024, 6, 15, 12, 30, 45, 123456)
        result = _normalize_value(dt)
        assert result == "2024-06-15T12:30:45.123+0000"

    def test_datetime_aware_is_converted_to_utc(self):
        from datetime import timezone as tz, timedelta
        eastern = timezone(timedelta(hours=-5))
        dt = datetime(2024, 6, 15, 7, 30, 45, 0, tzinfo=eastern)
        result = _normalize_value(dt)
        assert result == "2024-06-15T12:30:45.000+0000"

    def test_date_becomes_isoformat(self):
        d = date(2024, 1, 31)
        assert _normalize_value(d) == "2024-01-31"

    def test_decimal_becomes_float(self):
        d = decimal.Decimal("3.14159")
        result = _normalize_value(d)
        assert isinstance(result, float)
        assert abs(result - 3.14159) < 1e-5

    def test_uuid_becomes_lowercase_string(self):
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert _normalize_value(u) == "12345678-1234-5678-1234-567812345678"

    def test_int_passes_through(self):
        assert _normalize_value(99) == 99

    def test_float_passes_through(self):
        assert _normalize_value(1.5) == 1.5

    def test_str_passes_through(self):
        assert _normalize_value("hello") == "hello"

    def test_none_passes_through(self):
        assert _normalize_value(None) is None

    def test_bool_passes_through(self):
        assert _normalize_value(True) is True


# ---------------------------------------------------------------------------
# _normalize_row
# ---------------------------------------------------------------------------

class TestNormalizeRow:

    def test_produces_dict_with_correct_keys(self):
        cols = ("id", "state", "count")
        row = (uuid.UUID("12345678-1234-5678-1234-567812345678"), "active", 10)
        result = _normalize_row(cols, row)
        assert result == {
            "id": "12345678-1234-5678-1234-567812345678",
            "state": "active",
            "count": 10,
        }

    def test_mixed_types_all_normalised(self):
        cols = ("ts", "amount", "uid")
        row = (
            datetime(2024, 1, 1, 0, 0, 0),
            decimal.Decimal("99.99"),
            uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        )
        result = _normalize_row(cols, row)
        assert result["ts"] == "2024-01-01T00:00:00.000+0000"
        assert result["amount"] == pytest.approx(99.99)
        assert result["uid"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


# ---------------------------------------------------------------------------
# Client.query — happy paths
# ---------------------------------------------------------------------------

class TestClientQuery:

    def test_returns_list_of_dicts(self, client_instance):
        c, fake = client_instance
        fake._columns = ("id", "name")
        fake._rows = [("abc", "test")]

        result = c.query("analytics", "SELECT id, name FROM raw.foo")

        assert result == [{"id": "abc", "name": "test"}]

    def test_params_are_forwarded_to_ch_client(self, client_instance):
        c, fake = client_instance
        fake._rows = [(1,)]
        fake._columns = ("count",)

        c.query(
            "analytics",
            "SELECT COUNT(*) AS count FROM raw.policies WHERE app_id = {app_id:String}",
            params={"app_id": "uuid-123"},
        )

        assert len(fake.queries) == 1
        _, params, _ = fake.queries[0]
        assert params == {"app_id": "uuid-123"}

    def test_default_query_settings_applied(self, client_instance):
        c, fake = client_instance
        fake._rows = [(0,)]
        fake._columns = ("n",)

        c.query("analytics", "SELECT 0 AS n")

        _, _, settings = fake.queries[0]
        assert "max_execution_time" in settings
        assert settings["max_execution_time"] == 30  # default

    def test_caller_can_override_query_settings(self, client_instance):
        c, fake = client_instance
        fake._rows = [(0,)]
        fake._columns = ("n",)

        c.query(
            "analytics",
            "SELECT 0 AS n",
            query_settings={"max_execution_time": 120, "max_threads": 8},
        )

        _, _, settings = fake.queries[0]
        assert settings["max_execution_time"] == 120
        assert settings["max_threads"] == 8

    def test_empty_result_returns_empty_list(self, client_instance):
        c, fake = client_instance
        fake._rows = []
        fake._columns = ("count",)

        result = c.query("analytics", "SELECT COUNT(*) AS count FROM raw.nothing")
        assert result == []

    def test_multiple_rows_all_returned(self, client_instance):
        c, fake = client_instance
        fake._columns = ("state", "total")
        fake._rows = [("active", 100), ("canceled", 50)]

        result = c.query("analytics", "SELECT state, total FROM raw.summary")
        assert len(result) == 2
        assert result[0] == {"state": "active", "total": 100}
        assert result[1] == {"state": "canceled", "total": 50}


# ---------------------------------------------------------------------------
# Client.query — error handling
# ---------------------------------------------------------------------------

class TestClientQueryErrors:

    def test_empty_sql_raises_database_exception(self, client_instance):
        c, _ = client_instance
        with pytest.raises(DatabaseException, match="SQL query cannot be empty"):
            c.query("analytics", "")

    def test_whitespace_only_sql_raises_database_exception(self, client_instance):
        c, _ = client_instance
        with pytest.raises(DatabaseException):
            c.query("analytics", "   ")

    def test_unknown_server_key_raises_database_exception(self, client_instance):
        c, _ = client_instance
        with pytest.raises(DatabaseException, match="No configuration found"):
            c.query("nonexistent", "SELECT 1")

    def test_database_error_propagates_without_retry(self, client_instance, monkeypatch):
        """DatabaseError (bad SQL) must propagate immediately, no retry."""
        from clickhouse_connect.driver.exceptions import DatabaseError

        c, fake = client_instance
        fake._raise_on_query = DatabaseError("syntax error")

        with pytest.raises(DatabaseError):
            c.query("analytics", "SELECT garbage FROM")

        # Only one attempt — no retry on query-level errors.
        assert len(fake.queries) == 1

    def test_operational_error_triggers_reconnect_and_retry(
        self, monkeypatch, fake_ch_client
    ):
        """
        A transient operational error should trigger reconnect + retry.
        The second attempt succeeds.
        """
        conf = {
            "analytics": {
                "host": "localhost",
                "port": 8123,
                "db": "raw",
                "username": "default",
                "passwd": "",
            }
        }

        call_count = 0
        good_result = _make_query_result(("count",), [(7,)])

        def flaky_query(sql, parameters=None, settings=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("transient network error")
            return good_result

        fake_ch_client.query = flaky_query

        with patch("envoxy.clickhouse.client.clickhouse_connect") as mock_cc:
            mock_cc.get_client.return_value = fake_ch_client
            c = Client(conf)
            c._instances["analytics"]["ch_client"] = fake_ch_client

            # Override sleep to speed up test
            monkeypatch.setattr("envoxy.clickhouse.client.sleep", lambda _: None)

            result = c.query("analytics", "SELECT COUNT(*) AS count FROM raw.t")

        assert result == [{"count": 7}]
        assert call_count == 2  # failed once, succeeded on retry


# ---------------------------------------------------------------------------
# Client.reload_config
# ---------------------------------------------------------------------------

class TestReloadConfig:

    def test_new_server_key_is_connected(self, monkeypatch):
        conf = {
            "analytics": {
                "host": "localhost",
                "port": 8123,
                "db": "raw",
                "username": "default",
                "passwd": "",
            }
        }

        new_fake = FakeChClient()

        with patch("envoxy.clickhouse.client.clickhouse_connect") as mock_cc:
            mock_cc.get_client.return_value = FakeChClient()
            c = Client(conf)

            mock_cc.get_client.return_value = new_fake

            c.reload_config(
                {
                    "analytics": conf["analytics"],
                    "reporting": {
                        "host": "ch2.example.com",
                        "port": 8123,
                        "db": "raw",
                        "username": "default",
                        "passwd": "",
                    },
                }
            )

        assert "reporting" in c._instances

    def test_removed_server_key_is_closed(self, monkeypatch):
        conf = {
            "analytics": {
                "host": "localhost",
                "port": 8123,
                "db": "raw",
                "username": "default",
                "passwd": "",
            },
            "reporting": {
                "host": "ch2",
                "port": 8123,
                "db": "raw",
                "username": "default",
                "passwd": "",
            },
        }

        fake_reporting = FakeChClient()

        with patch("envoxy.clickhouse.client.clickhouse_connect") as mock_cc:
            mock_cc.get_client.return_value = FakeChClient()
            c = Client(conf)
            c._instances["reporting"]["ch_client"] = fake_reporting

            # Reload with only "analytics" — "reporting" should be removed + closed.
            c.reload_config({"analytics": conf["analytics"]})

        assert "reporting" not in c._instances
        assert fake_reporting.close_called

    def test_changed_config_triggers_reconnect(self, monkeypatch):
        conf = {
            "analytics": {
                "host": "old-host",
                "port": 8123,
                "db": "raw",
                "username": "default",
                "passwd": "",
            }
        }

        old_fake = FakeChClient()
        new_fake = FakeChClient()

        with patch("envoxy.clickhouse.client.clickhouse_connect") as mock_cc:
            mock_cc.get_client.return_value = old_fake
            c = Client(conf)
            c._instances["analytics"]["ch_client"] = old_fake

            mock_cc.get_client.return_value = new_fake

            c.reload_config(
                {
                    "analytics": {
                        "host": "new-host",  # changed
                        "port": 8123,
                        "db": "raw",
                        "username": "default",
                        "passwd": "",
                    }
                }
            )

        assert old_fake.close_called
        assert c._instances["analytics"]["ch_client"] is new_fake


# ---------------------------------------------------------------------------
# Singleton behaviour
# ---------------------------------------------------------------------------

class TestSingleton:

    def test_two_constructions_return_same_instance(self):
        conf = {
            "analytics": {
                "host": "localhost",
                "port": 8123,
                "db": "raw",
                "username": "default",
                "passwd": "",
            }
        }

        with patch("envoxy.clickhouse.client.clickhouse_connect") as mock_cc:
            mock_cc.get_client.return_value = FakeChClient()
            c1 = Client(conf)
            c2 = Client(conf)

        assert c1 is c2

    def test_singleton_safe_under_concurrent_access(self):
        conf = {
            "analytics": {
                "host": "localhost",
                "port": 8123,
                "db": "raw",
                "username": "default",
                "passwd": "",
            }
        }

        instances = []

        with patch("envoxy.clickhouse.client.clickhouse_connect") as mock_cc:
            mock_cc.get_client.return_value = FakeChClient()

            def create():
                instances.append(Client(conf))

            threads = [Thread(target=create) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # All threads must have received the exact same singleton.
        assert all(i is instances[0] for i in instances)
