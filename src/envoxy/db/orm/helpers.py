import re
from sqlalchemy import text

def to_sa_text(psycopg2_sql: str):
    """Convert a psycopg2-style SQL string with named placeholders
    (e.g. %(name)s) into a SQLAlchemy `text()` object using :name params.

    This helper is intentionally small and covers the common named-placeholder
    pattern used by existing code. It does NOT attempt to parse SQL fully;
    prefer writing queries with `:name` when possible.

    Args:
        psycopg2_sql: SQL string using `%(name)s` placeholders.

    Returns:
        sqlalchemy.sql.elements.TextClause: a `text()` object ready to bind.
    """

    # replace %(name)s with :name
    converted = re.sub(r"%\(([A-Za-z0-9_]+)\)s", r":\1", psycopg2_sql)
    return text(converted)
