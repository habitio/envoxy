# CI Tooling Helpers

Two minimal helpers are included for pipeline usage.

## check_migrations
Verify a versions directory exists and contains at least one migration.
```
python -m envoxy.tools.check_migrations path/to/versions
```
Exit codes: 0 ok, 2 path missing, 3 empty.

## validate_models
Scan a directory of JSON model descriptors and ensure required audit fields appear.
```
python -m envoxy.tools.validate_models path/to/models
```
Missing fields produce diagnostic lines and exit code 3.

## Suggested Pipeline Steps
1. Lint / type check
2. Run unit tests
3. `check_migrations` (if service owns DB schemas)
4. `validate_models` (if using JSON descriptor convention)
5. Build package / image
