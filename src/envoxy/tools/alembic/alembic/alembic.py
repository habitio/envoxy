"""Simple Python runner for the packaged alembic config.

This module can be invoked as a module to run alembic commands using the
packaged `alembic.ini`. Example:

    python -m envoxy.tools.alembic.alembic current

It avoids shell scripts and guarantees the currently active Python interpreter
is used (important when working inside virtualenvs).
"""
from __future__ import annotations

import sys
from importlib import resources


def _ini_path():
    pkg_root = resources.files("envoxy")
    return pkg_root.joinpath("tools", "alembic", "alembic.ini")


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    ini = _ini_path()

    try:
        from alembic.config import CommandLine
    except Exception as exc:  # pragma: no cover - env dependent
        print("ERROR: alembic is not installed in this environment:", exc, file=sys.stderr)
        print("Install with: pip install alembic", file=sys.stderr)
        return 2

    full_argv = ["-c", str(ini)] + argv
    # CommandLine.main may call sys.exit; propagate its return cleanly
    try:
        rc = CommandLine().main(full_argv)
        return int(rc or 0)
    except SystemExit as se:
        return int(getattr(se, 'code', 0) or 0)


if __name__ == "__main__":  # pragma: no cover - manual
    raise SystemExit(main())
