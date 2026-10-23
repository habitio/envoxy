# Logging and secret redaction

All `envoxy.log.*` output (and, in envoxyd, stdlib `logging` handlers) is passed
through an automatic redactor before it is written. It is **enabled by default**.

## What is masked

| Class | Examples | Mask |
|---|---|---|
| Passwords / secrets | `password`, `passwd`, `pwd`, `secret`, `client_secret`, `private_key` | `***` (never hashed) |
| Tokens / credentials | `Authorization`, `Bearer`/`Basic`, `Cookie`/`Set-Cookie`, `X-Api-Key`, `*token*` keys (`access_token`, `refresh_token`...), `api_key`, `confirmation_hash`, JWTs | `[REDACTED:len=N:<sha256[:8]>]` (same token => same id, so requests can be correlated) |
| URL credentials | `http://user:pass@host`, `postgresql://`, `redis://`, `amqp://`, `mongodb://`... | `scheme://user:***@host` |

It recognises JSON, Python `repr` of dicts, `key=value`, `key: value`, query strings and
header lines. Key names in `allow_keys` (default: `token_type`, `tokens_count`,
`next_page_token`...) are left untouched.

## Configuration (`log.redact` in the service `envoxy.json`)

```json
"log": {
  "level": "6",
  "redact": {
    "enabled": true,
    "mode": "hash",
    "keep": 4,
    "salt": "",
    "extra_headers": ["X-Muzzley-Key"],
    "extra_keys": ["card_number"],
    "extra_password_keys": [],
    "extra_patterns": ["sess=(?P<secret>\\w+)"],
    "allow_keys": ["my_token_label"],
    "replace_defaults": false
  }
}
```

* `mode`: `hash` (default), `partial` (`abcd***wxyz`, `keep` chars at each end, max 4) or `full` (`***`).
* `extra_patterns`: regexes; if a named group `secret` exists only that group is masked, otherwise the whole match.
* `replace_defaults`: use only the lists above instead of extending the built-in ones.
* Opt-out for local debugging: `"enabled": false` or the environment variable `ENVOXY_LOG_REDACT=0`
  (a boot warning is logged when disabled).

## Using it in service code

```python
import envoxy

envoxy.log.redact(text)                    # str -> str
envoxy.log.redact_mapping(headers)         # exact-key masking of dicts
envoxy.log.install_logging_redaction()     # attach the filter to stdlib root handlers (done by envoxyd)
```

Redaction is a safety net, not a guarantee: avoid logging credentials in the first place.
