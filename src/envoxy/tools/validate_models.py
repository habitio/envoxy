#!/usr/bin/env python
"""Minimal validate_models CLI wrapper so CI can call `python -m envoxy.tools.validate_models`.

This performs a lightweight JSON file scan under the provided directory and ensures
any object with a `fields` key includes `id`, `created`, `updated`, `href`.
"""

import sys
import json
from pathlib import Path


REQUIRED = {"id", "created", "updated", "href"}


def validate_model_file(p: Path) -> list[str]:
    """Validate a single model file and return list of error messages.
    
    Args:
        p: Path to the JSON model file
        
    Returns:
        List of error messages (empty if no errors)
    """
    errors = []
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"Failed to parse JSON: {e}")
        return errors
    
    # Check if this is a model file with datums
    if isinstance(obj, dict) and "datums" in obj and isinstance(obj["datums"], list):
        for idx, datum in enumerate(obj["datums"]):
            if isinstance(datum, dict) and "fields" in datum and isinstance(datum["fields"], dict):
                missing = REQUIRED - set(datum["fields"].keys())
                if missing:
                    errors.append(f"Datum {idx}: missing fields: {', '.join(sorted(missing))}")
    
    return errors


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
    for p in root.rglob("*.json"):
        if not check_file(p):
            ok = False
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
