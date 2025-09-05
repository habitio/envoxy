"""SQL types re-exports for convenience.

Allow imports like `from envoxy.db.orm.sqltypes import String, Integer, JSON,
Decimal, Float, DateTime`.
"""
from sqlalchemy.sql.sqltypes import (
	String,
	Integer,
	JSON,
	Float,
	DateTime,
	Date,
	Time,
	Boolean,
	Text,
	LargeBinary,
	Numeric,
	DECIMAL,
)

# Provide a familiar name alias 'Decimal' mapped to SQLAlchemy's Numeric
# which is commonly used for fixed-precision decimals.
Decimal = Numeric

__all__ = [
	"String",
	"Integer",
	"JSON",
	"Float",
	"DateTime",
	"Date",
	"Time",
	"Boolean",
	"Text",
	"LargeBinary",
	"Numeric",
	"DECIMAL",
	"Decimal",
]
