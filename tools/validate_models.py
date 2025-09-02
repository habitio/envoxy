"""Validate data-layer JSON model files for Envoxy conventions.

Usage:
    python tools/validate_models.py <path-to-models-folder>

This script verifies that every datum that defines `fields` includes the
required envoxy fields: id, created, updated, href.
"""
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = {'id', 'created', 'updated', 'href'}


def validate_model_file(path: Path):
    data = json.loads(path.read_text())
    errors = []

    datums = data.get('datums') or []
    for idx, datum in enumerate(datums):
        fields = datum.get('fields') or {}
        if not fields:
            # If model does not declare fields, skip validation for now
            continue

        missing = REQUIRED_FIELDS - set(fields.keys())
        if missing:
            errors.append(f"{path}: datum[{idx}] missing fields: {', '.join(sorted(missing))}")

    return errors


def main(paths):
    all_errors = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files = list(p.rglob('*.json'))
        else:
            files = [p]

        for f in files:
            all_errors.extend(validate_model_file(f))

    if all_errors:
        for e in all_errors:
            print('ERROR:', e)
        return 1

    print('OK: models validated')
    return 0


if __name__ == '__main__':
    paths = sys.argv[1:] or ['src/muzzley/data-layer/models']
    raise SystemExit(main(paths))
