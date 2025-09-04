"""Shared constants for the ORM layer."""

# Prefix used for all tables and indexes created by the thin data layer.
# Keep a single authoritative value here to avoid scattered string literals.
AUX_TABLE_PREFIX = 'aux_'

__all__ = ["AUX_TABLE_PREFIX"]
