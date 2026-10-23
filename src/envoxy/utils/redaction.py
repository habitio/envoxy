"""Automatic redaction of secrets in log messages.

Applied by ``Log.format_log`` / ``Log.system`` and, for stdlib loggers, by
``RedactingFilter``. Configured through the ``log.redact`` node of the service
configuration (see docs/LOGGING.md). Enabled by default.
"""

import hashlib
import logging
import os
import re
import traceback

_MAX_VALUE = 4096
_MAX_DEPTH = 6

# Keys whose values are never useful for correlation: always fully masked.
_PASSWORD_WORDS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "private_key",
    "private-key",
)

# High-entropy credentials: masked with a short hash so requests can be correlated.
_TOKEN_WORDS = (
    "token",
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "confirmation_hash",
    "session_id",
    "sessionid",
)

_DEFAULT_HEADERS = (
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
    "x-csrf-token",
    "x-amz-security-token",
    "api-key",
)

_DEFAULT_ALLOW_KEYS = (
    "token_type",
    "tokens_count",
    "token_count",
    "next_page_token",
    "page_token",
    "token_expires_in",
    "token_endpoint",
    "secret_name",
)

_SKIP_VALUES = {"", "none", "null", "true", "false", "nan"}
_FALSY_ENV = {"0", "false", "no", "off"}

_JWT_RE = re.compile(
    r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*"
)
_BEARER_RE = re.compile(
    r"\b(?P<scheme>Bearer|Basic|Digest)(?P<sp>\s+)(?P<val>[A-Za-z0-9._~+/=-]{8,})"
)
_URL_RE = re.compile(
    r"(?P<scheme>\b[A-Za-z][A-Za-z0-9+.-]*://)(?P<user>[^/\s:@'\"\\]+):(?P<pw>[^@\s/'\"\\]+)@"
)
_COOKIE_RE = re.compile(
    r"(?P<pre>(?<![\w-])(?:set-)?cookie(?P<q>['\"]?)\s*[:=]\s*)(?P<oq>['\"]?)(?P<val>[^'\"\n\x1b]{1,%d})"
    % _MAX_VALUE,
    re.IGNORECASE,
)


def _is_masked(value):
    return "***" in value or value.startswith("[REDACTED")


class Redactor:
    """Compiled redaction rules. Immutable after construction (thread safe)."""

    def __init__(self, cfg=None):
        cfg = cfg or {}

        self.enabled = bool(cfg.get("enabled", True))
        env = os.environ.get("ENVOXY_LOG_REDACT")
        if env is not None and env.strip().lower() in _FALSY_ENV:
            self.enabled = False

        self.mode = cfg.get("mode", "hash")
        if self.mode not in ("hash", "partial", "full"):
            self.mode = "hash"
        self.keep = max(1, min(int(cfg.get("keep", 4)), 4))
        self.salt = str(cfg.get("salt", ""))
        self.warnings = []

        replace = bool(cfg.get("replace_defaults", False))

        self.password_words = list(() if replace else _PASSWORD_WORDS)
        self.token_words = list(() if replace else _TOKEN_WORDS)
        self.headers = {
            h.lower() for h in (() if replace else _DEFAULT_HEADERS)
        } | {h.lower() for h in cfg.get("extra_headers", [])}
        self.allow_keys = {
            k.lower()
            for k in (() if replace else _DEFAULT_ALLOW_KEYS)
        } | {k.lower() for k in cfg.get("allow_keys", [])}
        self.token_words += [k.lower() for k in cfg.get("extra_keys", [])]
        self.token_words += [k.lower() for k in cfg.get("extra_token_keys", [])]
        self.password_words += [k.lower() for k in cfg.get("extra_password_keys", [])]
        self.token_words += list(self.headers - {"cookie", "set-cookie"})

        self.extra_patterns = []
        for pattern in cfg.get("extra_patterns", []):
            try:
                self.extra_patterns.append(re.compile(pattern))
            except re.error as e:
                self.warnings.append(
                    "invalid log.redact.extra_patterns entry %r ignored: %s" % (pattern, e)
                )

        words = sorted(
            set(self.password_words) | set(self.token_words), key=len, reverse=True
        )
        self._words = words

        if not words and not self.extra_patterns:
            self._kv_re = None
        else:
            alt = "|".join(re.escape(w) for w in words) if words else r"(?!)"
            self._kv_re = re.compile(
                r"(?P<pre>(?<![\w.-])(?P<q1>['\"]?)(?P<key>[\w.-]{0,64}?(?:%s)[\w.-]{0,64})(?P=q1)\s*[:=]\s*)"
                r"(?:(?P<q2>['\"])(?:(?P<scheme1>Bearer|Basic|Digest|Token)\s+)?(?P<qv>[^'\"\n\x1b]{1,%d})(?P=q2)"
                r"|(?:(?P<scheme2>Bearer|Basic|Digest|Token)\s+)?(?P<uv>[^\s'\",;&})\]\x1b]{1,%d}))"
                % (alt, _MAX_VALUE, _MAX_VALUE),
                re.IGNORECASE,
            )

        self._word_needles = tuple(words)

    # -- masking ----------------------------------------------------------

    def _token_mask(self, value):
        if self.mode == "full":
            return "***"
        if self.mode == "partial":
            if len(value) >= 4 * self.keep:
                return "%s***%s" % (value[: self.keep], value[-self.keep :])
            return "***"
        digest = hashlib.sha256((self.salt + value).encode("utf-8", "replace"))
        return "[REDACTED:len=%d:%s]" % (len(value), digest.hexdigest()[:8])

    def _is_password_key(self, key):
        key = key.lower()
        return any(w in key for w in self.password_words)

    def _mask_for_key(self, key, value):
        if self._is_password_key(key):
            return "***"
        return self._token_mask(value)

    # -- substitutions ----------------------------------------------------

    def _sub_kv(self, m):
        key = m.group("key")
        if key.lower() in self.allow_keys:
            return m.group(0)

        quoted = m.group("q2") is not None
        value = m.group("qv") if quoted else m.group("uv")
        scheme = m.group("scheme1") if quoted else m.group("scheme2")

        if value.lower() in _SKIP_VALUES or _is_masked(value) or len(value) < 3:
            return m.group(0)

        q = m.group("q2") or ""
        masked = self._mask_for_key(key, value)
        prefix = m.group("pre") + q
        if scheme:
            prefix += scheme + " "
        return prefix + masked + q

    def _sub_cookie(self, m):
        value = m.group("val")
        if _is_masked(value) or len(value) < 3:
            return m.group(0)
        return m.group("pre") + m.group("oq") + self._token_mask(value)

    def _sub_bearer(self, m):
        return m.group("scheme") + m.group("sp") + self._token_mask(m.group("val"))

    def _sub_url(self, m):
        if _is_masked(m.group("pw")):
            return m.group(0)
        return "%s%s:***@" % (m.group("scheme"), m.group("user"))

    def _sub_extra(self, m):
        if "secret" in (m.re.groupindex or {}) and m.group("secret"):
            start, end = m.span("secret")
            s = m.start()
            return m.group(0)[: start - s] + "***" + m.group(0)[end - s :]
        return "***"

    # -- public API -------------------------------------------------------

    def redact(self, text):
        """Return ``text`` with secrets masked. Idempotent; cheap when clean."""
        if not self.enabled or not text or len(text) < 6:
            return text

        lower = text.lower()

        out = text
        if "://" in lower and "@" in lower:
            out = _URL_RE.sub(self._sub_url, out)
        if "cookie" in lower:
            out = _COOKIE_RE.sub(self._sub_cookie, out)
        if self._kv_re is not None and any(w in lower for w in self._word_needles):
            out = self._kv_re.sub(self._sub_kv, out)
        if "bearer" in lower or "basic" in lower or "digest" in lower:
            out = _BEARER_RE.sub(self._sub_bearer, out)
        if "eyJ" in text:
            out = _JWT_RE.sub(lambda m: self._token_mask(m.group(0)), out)
        for pattern in self.extra_patterns:
            out = pattern.sub(self._sub_extra, out)
        return out

    def redact_mapping(self, mapping, _depth=0):
        """Exact-key redaction of a mapping (HTTP headers, params, payloads)."""
        if not self.enabled:
            return mapping
        if isinstance(mapping, dict):
            if _depth >= _MAX_DEPTH:
                return "***"
            result = {}
            for key, value in mapping.items():
                lkey = str(key).lower()
                if lkey in self.allow_keys:
                    result[key] = value
                elif isinstance(value, (dict, list, tuple)):
                    result[key] = self.redact_mapping(value, _depth + 1)
                elif lkey in self.headers or any(w in lkey for w in self._words):
                    text = value if isinstance(value, str) else str(value)
                    if text.lower() in _SKIP_VALUES or _is_masked(text):
                        result[key] = value
                    else:
                        result[key] = self._mask_for_key(lkey, text)
                elif isinstance(value, str):
                    result[key] = self.redact(value)
                else:
                    result[key] = value
            return result
        if isinstance(mapping, (list, tuple)):
            if _depth >= _MAX_DEPTH:
                return "***"
            items = [self.redact_mapping(v, _depth + 1) for v in mapping]
            return items if isinstance(mapping, list) else tuple(items)
        if isinstance(mapping, str):
            return self.redact(mapping)
        return mapping


_redactor = None
_REDACTED_FLAG = "envoxy_redacted"


def _load_config():
    try:
        from .config import Config

        log_conf = Config.get("log") or Config.get("$log") or {}
        return log_conf.get("redact") or {}
    except Exception:  # config unavailable (tests, scripts): use defaults
        return {}


def configure(cfg=None):
    """(Re)build the singleton from ``cfg`` (the ``log.redact`` dict)."""
    global _redactor
    _redactor = Redactor(cfg)
    return _redactor


def reset():
    """Forget the singleton so it is rebuilt from config on next use."""
    global _redactor
    _redactor = None


def get_redactor():
    global _redactor
    if _redactor is None:
        _redactor = Redactor(_load_config())
        _announce(_redactor)
    return _redactor


def _announce(redactor):
    messages = list(redactor.warnings)
    if not redactor.enabled:
        messages.append("log redaction is DISABLED: secrets may appear in clear text")
    if not messages:
        return
    try:
        from .logs import Log

        for message in messages:
            Log.system("[redaction] WARNING: %s\n" % message)
    except Exception:
        pass


class RedactingFilter(logging.Filter):
    """Stdlib logging filter masking secrets in message, args and exceptions."""

    def filter(self, record):
        if getattr(record, _REDACTED_FLAG, False):
            return True

        redactor = get_redactor()
        if not redactor.enabled:
            return True

        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)

        record.msg = redactor.redact(message)
        record.args = ()

        if record.exc_info and not record.exc_text:
            try:
                record.exc_text = redactor.redact(
                    "".join(traceback.format_exception(*record.exc_info)).rstrip("\n")
                )
            except Exception:
                pass
        elif record.exc_text:
            record.exc_text = redactor.redact(record.exc_text)

        if record.stack_info:
            record.stack_info = redactor.redact(record.stack_info)

        setattr(record, _REDACTED_FLAG, True)
        return True


def install_logging_redaction(logger=None):
    """Attach ``RedactingFilter`` to every handler of ``logger`` (default: root).

    Returns the number of handlers the filter was added to.
    """
    target = logger or logging.getLogger()
    added = 0
    for handler in target.handlers:
        if not any(isinstance(f, RedactingFilter) for f in handler.filters):
            handler.addFilter(RedactingFilter())
            added += 1
    return added
