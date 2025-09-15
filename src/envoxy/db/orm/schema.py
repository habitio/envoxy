"""Schema-level conveniences re-exported by `envoxy.db.orm.schema`.

Keep schema-level symbols (Column, Index) grouped separately from SQL
types so callers can import only what they need.

ForeignKey wrapper: allows using unprefixed table targets like
``ForeignKey("tpaagents.id")`` and automatically applies the framework's
auxiliary prefix (e.g., ``aux_<namespace>_tpaagents.id``) derived from
``ENVOXY_SERVICE_NAMESPACE``.
"""
from sqlalchemy.sql import schema as sa_schema
from sqlalchemy.sql.schema import Table as _SATable
from .constants import AUX_TABLE_PREFIX

# Re-export common schema symbols
Column = sa_schema.Column
Index = sa_schema.Index
UniqueConstraint = sa_schema.UniqueConstraint


def _prefix_table_if_needed(table_name: str) -> str:
	"""Apply AUX_TABLE_PREFIX to a bare table name if not already prefixed.

	- If the name already starts with AUX_TABLE_PREFIX or a generic 'aux_',
	  leave it unchanged to avoid double-prefixing.
	- Otherwise, return f"{AUX_TABLE_PREFIX}{table_name}".
	"""
	if not isinstance(table_name, str):  # defensive
		return table_name
	if table_name.startswith(AUX_TABLE_PREFIX) or table_name.startswith('aux_'):
		return table_name
	return f"{AUX_TABLE_PREFIX}{table_name}"


def ForeignKey(target, *args, **kwargs):  # noqa: N802 - keep SQLAlchemy name
	"""ForeignKey wrapper that auto-prefixes bare table targets.

	Examples:
	  - ForeignKey("tpaagents.id") -> ForeignKey("aux_<ns>_tpaagents.id")
	  - ForeignKey("schema.tpaagents.id") -> unchanged (schema-qualified)
	  - ForeignKey("aux_foo_tpaagents.id") -> unchanged (already prefixed)
	"""
	if isinstance(target, str):
		parts = target.split('.')
		if len(parts) == 2:
			table, col = parts
			target = f"{_prefix_table_if_needed(table)}.{col}"
		else:
			# If schema-qualified (schema.table.col), leave unchanged
			# or for any other atypical formatting, pass through.
			pass
	return sa_schema.ForeignKey(target, *args, **kwargs)


def prefixed(name: str) -> str:
	"""Return the AUX_TABLE_PREFIX-applied table name if needed."""
	return _prefix_table_if_needed(name)


def Table(name: str, *args, **kwargs):  # noqa: N802 - mirror SQLAlchemy API
	"""Wrapper around sqlalchemy.Table that auto-prefixes bare table names.

	Example:
		from envoxy.db.orm.schema import Table, Column, ForeignKey
		my = Table('tpaagents', metadata, Column('id', String(36), primary_key=True))
	"""
	return _SATable(_prefix_table_if_needed(name), *args, **kwargs)


__all__ = ["Column", "Index", "ForeignKey", "UniqueConstraint", "Table", "prefixed"]
