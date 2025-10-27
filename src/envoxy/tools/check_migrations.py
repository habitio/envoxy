#!/usr/bin/env python
"""Minimal check_migrations CLI wrapper.

This script verifies that a migrations versions directory exists and contains files.
It's intentionally small: the deeper framework checks can be added later.
"""

import sys
from pathlib import Path


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m envoxy.tools.check_migrations <versions_dir>")
        return 2
    p = Path(argv[0])
    if not p.exists() or not p.is_dir():
        print(f"Migrations directory not found: {p}")
        return 2
    entries = [x for x in p.iterdir() if x.is_file()]
    if not entries:
        print(f"No migration files found in {p}")
        return 3
    print(f"Found {len(entries)} migration files in {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
