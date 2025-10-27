from sqlalchemy.sql.schema import (
    Column,
    Index,
    UniqueConstraint,
    ForeignKeyConstraint,
    CheckConstraint,
    PrimaryKeyConstraint,
)
from sqlalchemy.sql.sqltypes import String, DateTime
from .constants import AUX_TABLE_PREFIX
import re
import hashlib
from typing import Sequence

try:  # Optional: Postgres-specific constraint
    from sqlalchemy.dialects.postgresql import ExcludeConstraint as PGExcludeConstraint  # type: ignore
except Exception:  # pragma: no cover
    PGExcludeConstraint = None  # type: ignore


class EnvoxyMixin:
    """Base mixin adding audit columns and enforcing naming conventions.

    Responsibilities:
    - Provide id/created/updated/href columns.
    - Normalize Index and UniqueConstraint names with the service prefix.
    - Auto-prefix string-based ForeignKey targets with service prefix.
    """

    # Prevent SQLAlchemy from mapping this mixin as a concrete table.
    __abstract__ = True

    # Standard audit fields
    id = Column("id", String(36), primary_key=True)
    created = Column("created", DateTime, nullable=False)
    updated = Column("updated", DateTime, nullable=False)
    href = Column("href", String(1024), nullable=False)

    # ---------------------- helpers (pure/side-effect free) ----------------------
    @staticmethod
    def _is_prefixed_table(name: str) -> bool:
        return name.startswith(AUX_TABLE_PREFIX) or name.startswith("aux_")

    @staticmethod
    def _deprefixed_table(name: str) -> str:
        return (
            name[len(AUX_TABLE_PREFIX) :] if name.startswith(AUX_TABLE_PREFIX) else name
        )

    @staticmethod
    def _shorten_identifier(s: str) -> str:
        # Postgres 63-char limit; keep 60 + 8-char hash safeguard
        if len(s) <= 60:
            return s
        h = hashlib.sha1(s.encode()).hexdigest()[:8]
        return f"{s[:51]}_{h}"

    @staticmethod
    def _sanitize_identifier(s: str) -> str:
        """Normalize identifier: lowercase and replace non [a-z0-9_] with _."""
        return re.sub(r"[^a-z0-9_]", "_", s.lower())

    @classmethod
    def _make_index_name(cls, cols: Sequence[str]) -> str:
        tname = cls._deprefixed_table(getattr(cls, "__tablename__", "table") or "table")
        base = f"idx_{tname}_{'_'.join(cols) if cols else 'expr'}"
        safe = cls._sanitize_identifier(base)
        return cls._shorten_identifier(safe)

    @classmethod
    def _make_unique_name(cls, cols: Sequence[str]) -> str:
        tname = cls._deprefixed_table(getattr(cls, "__tablename__", "table") or "table")
        base = f"uq_{tname}_{'_'.join(cols) if cols else 'cols'}"
        safe = cls._sanitize_identifier(base)
        return cls._shorten_identifier(safe)

    @classmethod
    def _make_fk_name(cls, local_cols: Sequence[str], ref_tables: Sequence[str]) -> str:
        tname = cls._deprefixed_table(getattr(cls, "__tablename__", "table") or "table")
        ref = ref_tables[0] if ref_tables else "ref"
        base = f"fk_{tname}_{'_'.join(local_cols) if local_cols else 'col'}_to_{ref}"
        safe = cls._sanitize_identifier(base)
        return cls._shorten_identifier(safe)

    @classmethod
    def _make_check_name(cls, expr_text: str | None) -> str:
        tname = cls._deprefixed_table(getattr(cls, "__tablename__", "table") or "table")
        h = hashlib.sha1((expr_text or "ck").encode()).hexdigest()[:8]
        base = f"ck_{tname}_{h}"
        safe = cls._sanitize_identifier(base)
        return cls._shorten_identifier(safe)

    @classmethod
    def _make_pk_name(cls) -> str:
        tname = cls._deprefixed_table(getattr(cls, "__tablename__", "table") or "table")
        base = f"pk_{tname}"
        safe = cls._sanitize_identifier(base)
        return cls._shorten_identifier(safe)

    @classmethod
    def _make_exclude_name(cls, cols: Sequence[str]) -> str:
        tname = cls._deprefixed_table(getattr(cls, "__tablename__", "table") or "table")
        base = f"ex_{tname}_{'_'.join(cols) if cols else 'expr'}"
        safe = cls._sanitize_identifier(base)
        return cls._shorten_identifier(safe)

    @staticmethod
    def _prefix_fk_spec(spec: str) -> str:
        if not isinstance(spec, str):
            return spec
        parts = spec.split(".")
        # Only prefix when unqualified (table.column)
        if len(parts) == 2:
            table, col = parts
            if table and not EnvoxyMixin._is_prefixed_table(table):
                table = AUX_TABLE_PREFIX + table
            return f"{table}.{col}"
        return spec  # schema-qualified or other forms

    # ---------------------- normalization entrypoints ----------------------
    @classmethod
    def _normalize_indexes_and_uniques(cls) -> None:
        table_args = getattr(cls, "__table_args__", None)
        if not table_args:
            return
        new_args = []
        for arg in table_args:
            if isinstance(arg, Index):
                name = getattr(arg, "name", None)
                if not (isinstance(name, str) and name):
                    # derive from expressions
                    col_parts = [
                        getattr(e, "name", str(e))
                        for e in (getattr(arg, "expressions", []) or [])
                    ]
                    arg.name = AUX_TABLE_PREFIX + cls._make_index_name(col_parts)
                elif not name.startswith(AUX_TABLE_PREFIX):
                    arg.name = AUX_TABLE_PREFIX + name
                new_args.append(arg)
            elif isinstance(arg, UniqueConstraint):
                name = getattr(arg, "name", None)
                if not (isinstance(name, str) and name):
                    col_parts: list[str] = []
                    try:
                        for c in list(getattr(arg, "columns", []) or []):
                            col_parts.append(getattr(c, "name", str(c)))
                    except Exception:
                        pass
                    arg.name = AUX_TABLE_PREFIX + cls._make_unique_name(col_parts)
                elif not name.startswith(AUX_TABLE_PREFIX):
                    arg.name = AUX_TABLE_PREFIX + name
                new_args.append(arg)
            else:
                new_args.append(arg)
        cls.__table_args__ = tuple(new_args)

    @classmethod
    def _normalize_foreign_keys(cls) -> None:
        # Column-level FKs
        for _name, value in list(getattr(cls, "__dict__", {}).items()):
            if isinstance(value, Column):
                fks = getattr(value, "foreign_keys", None)
                if not fks:
                    continue
                try:
                    iterable = fks if isinstance(fks, (set, tuple, list)) else list(fks)  # type: ignore[arg-type]
                    for fk in iterable:
                        colspec = getattr(fk, "_colspec", None)
                        if isinstance(colspec, str):
                            new_spec = cls._prefix_fk_spec(colspec)
                            if new_spec != colspec:
                                setattr(fk, "_colspec", new_spec)
                except Exception:
                    pass

        # Table-level ForeignKeyConstraints in __table_args__
        table_args = getattr(cls, "__table_args__", None)
        if not table_args:
            return
        patched_args = []
        for arg in table_args:
            if isinstance(arg, ForeignKeyConstraint):
                try:
                    for fk in getattr(arg, "elements", []) or []:
                        colspec = getattr(fk, "_colspec", None)
                        if isinstance(colspec, str):
                            new_spec = cls._prefix_fk_spec(colspec)
                            if new_spec != colspec:
                                setattr(fk, "_colspec", new_spec)
                    # Normalize FK constraint names
                    name = getattr(arg, "name", None)
                    if not (isinstance(name, str) and name):
                        local_cols: list[str] = []
                        try:
                            for c in list(getattr(arg, "columns", []) or []):
                                local_cols.append(getattr(c, "name", str(c)))
                        except Exception:
                            pass
                        ref_tables: list[str] = []
                        try:
                            for e in getattr(arg, "elements", []) or []:
                                spec = getattr(e, "_colspec", None) or getattr(
                                    e, "target_fullname", ""
                                )
                                if isinstance(spec, str) and "." in spec:
                                    table = spec.split(".")[0]
                                    table = cls._deprefixed_table(table)
                                    ref_tables.append(table)
                        except Exception:
                            pass
                        arg.name = AUX_TABLE_PREFIX + cls._make_fk_name(
                            local_cols, ref_tables
                        )
                    elif not name.startswith(AUX_TABLE_PREFIX):
                        arg.name = AUX_TABLE_PREFIX + name
                except Exception:
                    pass
                patched_args.append(arg)
            else:
                patched_args.append(arg)
        cls.__table_args__ = tuple(patched_args)

        # Also normalize names for CheckConstraint and PrimaryKeyConstraint
        table_args = getattr(cls, "__table_args__", None)
        if not table_args:
            return
        normalized: list = []
        for arg in table_args:
            if isinstance(arg, CheckConstraint):
                name = getattr(arg, "name", None)
                if not (isinstance(name, str) and name):
                    expr = None
                    try:
                        expr = str(getattr(arg, "sqltext", "") or "")
                    except Exception:
                        pass
                    arg.name = AUX_TABLE_PREFIX + cls._make_check_name(expr)
                elif not name.startswith(AUX_TABLE_PREFIX):
                    arg.name = AUX_TABLE_PREFIX + name
                normalized.append(arg)
            elif isinstance(arg, PrimaryKeyConstraint):
                name = getattr(arg, "name", None)
                if not (isinstance(name, str) and name):
                    arg.name = AUX_TABLE_PREFIX + cls._make_pk_name()
                elif not name.startswith(AUX_TABLE_PREFIX):
                    arg.name = AUX_TABLE_PREFIX + name
                normalized.append(arg)
            elif PGExcludeConstraint is not None and isinstance(
                arg, PGExcludeConstraint
            ):  # type: ignore
                name = getattr(arg, "name", None)
                if not (isinstance(name, str) and name):
                    col_parts: list[str] = []
                    try:
                        for c in list(getattr(arg, "columns", []) or []):
                            col_parts.append(getattr(c, "name", str(c)))
                    except Exception:
                        pass
                    arg.name = AUX_TABLE_PREFIX + cls._make_exclude_name(col_parts)
                elif not name.startswith(AUX_TABLE_PREFIX):
                    arg.name = AUX_TABLE_PREFIX + name
                normalized.append(arg)
            else:
                normalized.append(arg)
        cls.__table_args__ = tuple(normalized)

    # ---------------------- SQLAlchemy hook ----------------------
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._normalize_indexes_and_uniques()
        cls._normalize_foreign_keys()
