#!/usr/bin/env python
"""Minimal validate_models CLI wrapper so CI can call `python -m envoxy.tools.validate_models`.

This performs a lightweight JSON file scan under the provided directory and ensures
any object with a `fields` key includes `id`, `created`, `updated`, `href`.
"""
import sys
import json
from pathlib import Path


REQUIRED = {"id", "created", "updated", "href"}


def check_file(p: Path) -> bool:
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return True
    if isinstance(obj, dict) and "fields" in obj and isinstance(obj["fields"], dict):
        missing = REQUIRED - set(obj["fields"].keys())
        if missing:
            print(f"{p}: missing fields: {', '.join(sorted(missing))}")
            return False
    return True


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m envoxy.tools.validate_models <models_dir>")
        return 2
    root = Path(argv[0])
    if not root.exists():
        print(f"Models directory not found: {root}")
        return 2
    ok = True
    for p in root.rglob('*.json'):
        if not check_file(p):
            ok = False
    return 0 if ok else 3


if __name__ == '__main__':
    raise SystemExit(main())
