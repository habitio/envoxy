"""SQL types re-exports for convenience.

Allow imports like `from envoxy.db.orm.sqltypes import String, Integer, JSON,
Decimal, Float, DateTime`.
"""

from sqlalchemy.sql.sqltypes import (
    String,
    Unicode,
    UnicodeText,
    Text,
    Integer,
    SmallInteger,
    BigInteger,
    Numeric,
    DECIMAL,
    Float,
    Boolean,
    Date,
    Time,
    DateTime,
    Interval,
    JSON,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

# Provide a familiar name alias 'Decimal' mapped to SQLAlchemy's Numeric
# which is commonly used for fixed-precision decimals.
Decimal = Numeric

__all__ = [
    "String",
    "Unicode",
    "UnicodeText",
    "Text",
    "Integer",
    "SmallInteger",
    "BigInteger",
    "Numeric",
    "DECIMAL",
    "Decimal",
    "Float",
    "Boolean",
    "Date",
    "Time",
    "DateTime",
    "Interval",
    "JSON",
    "Enum",
    # Postgres dialect types
    "UUID",
    "JSONB",
    "ARRAY",
]
