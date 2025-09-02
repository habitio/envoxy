"""Alembic hooks for enforcing Envoxy table pattern during autogenerate.

Usage: import `check_op` from this module in your alembic env.py and call it
during autogenerate to validate operations in the migration context.
"""
def check_autogenerate_revision(revision_context):
    """
    Inspect the autogenerate revision context (alembic.autogenerate.api.RevisionContext)
    and raise ValueError if a CREATE TABLE operation lacks required columns.
    """
    ops = getattr(revision_context, 'ops', None)
    if ops is None:
        return

    REQUIRED_COLUMNS = {'id', 'created', 'updated', 'href'}
    # allowed SQLAlchemy type names (a subset, adjust as needed)
    ALLOWED_TYPE_NAMES = {
        'String', 'VARCHAR', 'TEXT', 'Integer', 'BigInteger', 'Boolean', 'DateTime', 'JSON', 'JSONB'
    }

    def _check_create_op(op):
        if op.__class__.__name__ == 'CreateTableOp':
            colnames = {c.name for c in op.columns}
            missing = REQUIRED_COLUMNS - colnames
            if missing:
                raise ValueError(f"CreateTable operation for {op.name} is missing required columns: {', '.join(sorted(missing))}")

            # check column types are allowed (best-effort)
            for c in op.columns:
                t = getattr(c, 'type', None)
                if t is None:
                    continue
                tname = type(t).__name__
                if tname.upper() not in (n.upper() for n in ALLOWED_TYPE_NAMES):
                    # allow types that look like String(length) etc by name
                    raise ValueError(f"CreateTable {op.name}: column {c.name} has disallowed type {tname}")

    for op in ops.ops:
        try:
            _check_create_op(op)
        except Exception:
            raise
