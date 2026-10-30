"""Unit tests for envoxy.utils.redaction and its Log integration."""

import importlib.util
import json
import logging
import os
import sys
import time
import types

import pytest

_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "src", "envoxy", "utils")


def _load(name):
    spec = importlib.util.spec_from_file_location(
        "_redaction_under_test", os.path.join(_SRC, name)
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


redaction = _load("redaction.py")
Redactor = redaction.Redactor

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r"


@pytest.fixture
def r():
    return Redactor({})


def hide(out, *secrets):
    for s in secrets:
        assert s not in out, f"{s!r} leaked in {out!r}"


class TestRules:
    def test_bearer_header_in_dict_repr(self, r):
        out = r.redact("Headers:{'Authorization': 'Bearer " + JWT + "', 'Host': 'x'}")
        hide(out, JWT, "dBjftJ")
        assert "'Authorization': 'Bearer [REDACTED:len=" in out
        assert "'Host': 'x'" in out

    def test_header_line(self, r):
        out = r.redact("Authorization: Bearer abcdef1234567890")
        hide(out, "abcdef1234567890")
        assert out.startswith("Authorization: Bearer [REDACTED:")

    def test_basic_auth(self, r):
        out = r.redact("Authorization: Basic dXNlcjpwYXNzd29yZA==")
        hide(out, "dXNlcjpwYXNzd29yZA")

    def test_cookie(self, r):
        out = r.redact("Cookie: sid=abc123def; other=zzz999")
        hide(out, "abc123def", "zzz999")
        out = r.redact("{'Set-Cookie': 'sid=abc123def; Path=/'}")
        hide(out, "abc123def")

    def test_api_key_header(self, r):
        hide(r.redact("{'X-Api-Key': 'k-123456789'}"), "k-123456789")

    @pytest.mark.parametrize(
        "text,secret",
        [
            ('{"password": "hunter2"}', "hunter2"),
            ("{'password': 'hunter2'}", "hunter2"),
            ("password=hunter2&user=bob", "hunter2"),
            ("password: hunter2", "hunter2"),
            ('{"access_token": "abc.def.ghi"}', "abc.def.ghi"),
            ("GET /x?access_token=abcdef123456&a=1", "abcdef123456"),
            ('{"confirmation_hash": "deadbeef0123"}', "deadbeef0123"),
            ('{"client_secret": "s3cr3t-value"}', "s3cr3t-value"),
            ('{"refresh_token": "r-1234567"}', "r-1234567"),
            ("Payload{\"user\": {\"password\": \"hunter2\"}}", "hunter2"),
        ],
    )
    def test_keys(self, r, text, secret):
        hide(r.redact(text), secret)

    def test_password_is_fully_masked_not_hashed(self, r):
        out = r.redact('{"password": "hunter2"}')
        assert out == '{"password": "***"}'

    def test_token_hash_is_stable_for_correlation(self, r):
        a = r.redact("Bearer abcdef1234567890")
        b = r.redact("x Bearer abcdef1234567890 y")
        assert a.split()[1] in b

    def test_jwt_in_free_text(self, r):
        out = r.redact("got " + JWT + " from upstream")
        hide(out, JWT)

    @pytest.mark.parametrize(
        "url",
        [
            "http://admin:p4ss@couch:5984",
            "postgresql://u:p4ss@db/x",
            "redis://:p4ss@h" if False else "redis://u:p4ss@h:6379/0",
            "amqp://u:p4ss@h//",
            "mongodb+srv://u:p4ss@c.example.net/db",
        ],
    )
    def test_url_userinfo(self, r, url):
        out = r.redact(f"CouchDB::execute_request - Request: {url} {{}}")
        hide(out, "p4ss")
        assert "u:***@" in out or "admin:***@" in out

    def test_url_without_password_untouched(self, r):
        text = "https://host/path?mail=a@b.c"
        assert r.redact(text) == text

    def test_ansi_wrapped(self, r):
        out = r.redact("\x1b[1m> Request\x1b[0m | Headers:{'Authorization': 'Bearer abcdefgh12345'}")
        hide(out, "abcdefgh12345")
        assert "\x1b[0m" in out

    @pytest.mark.parametrize(
        "text",
        [
            "{'token_type': 'bearer'}",
            '{"tokens_count": 12345}',
            '{"next_page_token": "abcdefgh12345"}',
            "no secrets here, just a normal message",
            "request took 0.12 sec",
            "{'_id': '8f14e45f-ceea-467f-a0e6-bb7a3f1b4c0e'}",
            "password: ",
            '{"password": null}',
        ],
    )
    def test_no_false_positive(self, r, text):
        assert r.redact(text) == text


class TestIdempotence:
    SAMPLES = [
        "Headers:{'Authorization': 'Bearer abcdef1234567890', 'Cookie': 'sid=abcdef123'}",
        '{"password": "hunter2", "access_token": "abcdef1234567890"}',
        "http://admin:p4ss@couch:5984 and " + JWT,
        "password=hunter2&access_token=abcdef123456",
    ]

    @pytest.mark.parametrize("mode", ["hash", "partial", "full"])
    @pytest.mark.parametrize("text", SAMPLES)
    def test_idempotent(self, mode, text):
        rd = Redactor({"mode": mode})
        once = rd.redact(text)
        assert rd.redact(once) == once


class TestModes:
    def test_partial(self):
        out = Redactor({"mode": "partial", "keep": 4}).redact("Bearer abcdefghijklmnopqrstuvwxyz")
        assert "abcd***wxyz" in out and "efghijkl" not in out

    def test_partial_short_value_fully_masked(self):
        out = Redactor({"mode": "partial", "keep": 4}).redact('{"token": "abcdefgh"}')
        assert out == '{"token": "***"}'

    def test_full(self):
        assert Redactor({"mode": "full"}).redact("Bearer abcdefghijkl") == "Bearer ***"

    def test_salt_changes_hash(self):
        a = Redactor({}).redact("Bearer abcdefghijkl")
        b = Redactor({"salt": "x"}).redact("Bearer abcdefghijkl")
        assert a != b


class TestConfig:
    def test_disabled(self):
        text = "Bearer abcdefghijkl"
        assert Redactor({"enabled": False}).redact(text) == text

    def test_env_opt_out(self, monkeypatch):
        monkeypatch.setenv("ENVOXY_LOG_REDACT", "0")
        text = "Bearer abcdefghijkl"
        assert Redactor({}).redact(text) == text

    def test_extra_keys_headers_patterns_and_allow(self):
        rd = Redactor(
            {
                "extra_keys": ["card_number"],
                "extra_headers": ["X-Muzzley-Key"],
                "extra_patterns": [r"sess=(?P<secret>\w+)"],
                "allow_keys": ["my_token_label"],
            }
        )
        hide(rd.redact('{"card_number": "4111111111111111"}'), "4111111111111111")
        hide(rd.redact("{'X-Muzzley-Key': 'abcdefgh1234'}"), "abcdefgh1234")
        out = rd.redact("cookie-less sess=abcd1234 end")
        hide(out, "abcd1234")
        assert "sess=***" in out
        text = '{"my_token_label": "visible-value"}'
        assert rd.redact(text) == text

    def test_invalid_pattern_ignored_with_warning(self):
        rd = Redactor({"extra_patterns": ["("]})
        assert rd.warnings and rd.redact("hello world") == "hello world"

    def test_replace_defaults(self):
        rd = Redactor({"replace_defaults": True, "extra_keys": ["foo"]})
        assert "hunter2" in rd.redact('{"password": "hunter2"}')
        hide(rd.redact('{"foo": "bar-secret"}'), "bar-secret")


class TestMapping:
    def test_headers(self, r):
        out = r.redact_mapping(
            {"Authorization": "Bearer abcdefgh1234", "Host": "x", "Cookie": "a=b123"}
        )
        assert out["Host"] == "x"
        hide(str(out), "abcdefgh1234", "a=b123")

    def test_nested_and_input_not_mutated(self, r):
        data = {"user": {"password": "hunter2", "name": "bob"}, "l": [{"token": "abcdefgh"}]}
        out = r.redact_mapping(data)
        hide(str(out), "hunter2", "abcdefgh")
        assert data["user"]["password"] == "hunter2"
        assert out["user"]["name"] == "bob"


class TestStdlibFilter:
    def _record(self, msg, args=(), exc_info=None):
        return logging.LogRecord("t", logging.ERROR, __file__, 1, msg, args, exc_info)

    def setup_method(self):
        redaction.configure({})

    def test_args_and_dict(self):
        rec = self._record("auth %s", ({"Authorization": "Bearer abcdefgh1234"},))
        redaction.RedactingFilter().filter(rec)
        hide(rec.getMessage(), "abcdefgh1234")

    def test_exception_text(self):
        try:
            raise ValueError("connect to http://u:p4ss@host failed")
        except ValueError:
            import sys as _s

            rec = self._record("boom", exc_info=_s.exc_info())
        redaction.RedactingFilter().filter(rec)
        hide(rec.exc_text, "p4ss")
        fmt = logging.Formatter("%(message)s").format(rec)
        hide(fmt, "p4ss")

    def test_flag_prevents_reprocessing(self):
        rec = self._record("Bearer abcdefghijkl")
        rec.envoxy_redacted = True
        redaction.RedactingFilter().filter(rec)
        assert rec.msg == "Bearer abcdefghijkl"

    def test_install(self):
        lg = logging.getLogger("redact-install-test")
        lg.addHandler(logging.NullHandler())
        assert redaction.install_logging_redaction(lg) == 1
        assert redaction.install_logging_redaction(lg) == 0


class TestPerformance:
    def test_clean_message_fast(self, r):
        text = "ZMQ::send_and_recv::time:: tcp://127.0.0.1:5555 :: 0.01 :: ok " * 3
        n = 5000
        t = time.perf_counter()
        for _ in range(n):
            r.redact(text)
        per_call = (time.perf_counter() - t) / n
        assert per_call < 50e-6

    def test_large_with_secrets_and_no_redos(self, r):
        text = ("x" * 50 + " Bearer abcdefghijkl password=hunter2 ") * 100
        t = time.perf_counter()
        r.redact(text)
        assert time.perf_counter() - t < 0.5
        evil = "password" + "=" * 20000 + "a" * 20000 + ":" * 20000
        t = time.perf_counter()
        r.redact(evil)
        assert time.perf_counter() - t < 1.0


class TestLogIntegration:
    @pytest.fixture
    def log_mod(self, monkeypatch):
        """Load logs.py with a fake uwsgi and a package context for relative imports."""
        pkg = types.ModuleType("_envox")
        pkg.__path__ = [_SRC]
        monkeypatch.setitem(sys.modules, "_envox", pkg)
        sink = []
        fake = types.SimpleNamespace(
            log=sink.append, opt={"log-level": b"\x09"}
        )
        monkeypatch.setitem(sys.modules, "uwsgi", fake)
        for name in ("datetime", "config", "redaction", "logs"):
            spec = importlib.util.spec_from_file_location(
                f"_envox.{name}", os.path.join(_SRC, f"{name}.py")
            )
            mod = importlib.util.module_from_spec(spec)
            monkeypatch.setitem(sys.modules, spec.name, mod)
            spec.loader.exec_module(mod)
        sys.modules["_envox.redaction"].reset()
        return sys.modules["_envox.logs"], sink

    def test_log_levels_emit_valid_json_without_secrets(self, log_mod):
        logs, sink = log_mod
        L = logs.Log
        secret_url = "http://admin:p4ss@couch:5984"
        L.debug(f"CouchDB::execute_request - Request: {secret_url} {{}}")
        L.verbose("Headers:{'Authorization': 'Bearer abcdefgh12345'}")
        L.error('{"password": "hunter2"}')
        L.system("boot password=hunter2")
        assert len(sink) == 4
        for line in sink[:3]:
            hide(line, "p4ss", "abcdefgh12345", "hunter2")
            json.loads(line)
        hide(sink[3], "hunter2")

    def test_truncation_does_not_reintroduce(self, log_mod):
        logs, sink = log_mod
        text = "\n".join(["a"] * 50 + ["password=hunter2"] + ["b"] * 50)
        logs.Log.info(text, max_lines=10)
        hide(sink[0], "hunter2")
