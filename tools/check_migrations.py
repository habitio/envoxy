"""Scan alembic migration scripts and enforce envoxy table patterns.

This script inspects Python migration files under alembic/versions for `op.create_table`
calls and validates that the created table includes the required columns and allowed types.

Usage: python tools/check_migrations.py [path-to-alembic-versions]
"""
import ast
import sys
from pathlib import Path

REQUIRED_COLUMNS = {'id', 'created', 'updated', 'href'}
ALLOWED_TYPE_NAMES = {'String', 'VARCHAR', 'TEXT', 'Integer', 'BigInteger', 'Boolean', 'DateTime', 'JSON', 'JSONB'}


def _get_create_table_calls(node):
    calls = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            func = n.func
            # detect op.create_table or alembic.op.create_table
            if isinstance(func, ast.Attribute) and func.attr == 'create_table':
                calls.append(n)
    return calls


def _extract_columns_from_call(call_node):
    # naive parse: look at positional args after first (table name)
    cols = []
    for arg in call_node.args[1:]:
        # Column('name', types.XYZ, ...)
        if isinstance(arg, ast.Call) and getattr(arg.func, 'id', '') == 'Column':
            name = None
            coltype = None
            if arg.args:
                # first arg: column name
                if isinstance(arg.args[0], ast.Constant):
                    name = arg.args[0].value
                elif isinstance(arg.args[0], ast.Str):
                    name = arg.args[0].s
            # second positional arg may be type
            if len(arg.args) >= 2:
                t = arg.args[1]
                if isinstance(t, ast.Name):
                    coltype = t.id
                elif isinstance(t, ast.Attribute):
                    coltype = t.attr
            cols.append((name, coltype))
    return cols


def check_file(path: Path):
    text = path.read_text()
    tree = ast.parse(text)
    calls = _get_create_table_calls(tree)
    errors = []
    for call in calls:
        # first arg should be table name
        table_name = None
        if call.args and isinstance(call.args[0], ast.Constant):
            table_name = call.args[0].value
        cols = _extract_columns_from_call(call)
        colnames = {c[0] for c in cols if c[0]}
        missing = REQUIRED_COLUMNS - colnames
        if missing:
            errors.append(f"{path}: create_table {table_name} missing columns: {', '.join(sorted(missing))}")
        for name, ctype in cols:
            if ctype and ctype not in ALLOWED_TYPE_NAMES:
                errors.append(f"{path}: create_table {table_name} column {name} has disallowed type {ctype}")
    return errors


def main(versions_dir: Path):
    if not versions_dir.exists():
        print(f"No migrations dir at {versions_dir}; skipping")
        return 0
    errors = []
    for f in versions_dir.glob('*.py'):
        errors.extend(check_file(f))
    if errors:
        for e in errors:
            print('ERROR:', e)
        return 1
    print('OK: migrations validated')
    return 0


if __name__ == '__main__':
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('alembic/versions')
    raise SystemExit(main(p))
