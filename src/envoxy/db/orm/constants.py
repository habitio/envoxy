"""Shared constants for the ORM layer."""

from __future__ import annotations

import os
import re


def _compute_aux_table_prefix() -> str:
		"""Derive the managed table prefix from ENVOXY_SERVICE_NAMESPACE.

		- When ENVOXY_SERVICE_NAMESPACE is set, returns "aux_<ns>_".
		- Otherwise, falls back to plain "aux_" (runtime-safe; Alembic enforces
			the namespace in migration runs).
		"""
		ns = os.getenv("ENVOXY_SERVICE_NAMESPACE", "").strip().lower()
		if not ns:
				return "aux_"
		ns = re.sub(r"[^a-z0-9_]", "_", ns)
		return f"aux_{ns}_"


# Prefix used for all tables created by the thin data layer. Computed once at
# import time so SQLAlchemy declaratives pick it up during class mapping.
AUX_TABLE_PREFIX = _compute_aux_table_prefix()

__all__ = ["AUX_TABLE_PREFIX"]
