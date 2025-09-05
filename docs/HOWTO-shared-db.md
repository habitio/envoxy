# Shared Database Guidance

Multiple services can share a database while respecting Envoxy conventions.

## Goals
- Avoid table name collisions (prefix `aux_` + pluralization)
- Keep migration history coherent per service
- Allow read‑only consumers alongside write owners

## Recommendations
1. Each service has its own Alembic versions directory (separate history trees).
2. Never rename a table outside of a migration (rely on generated operations).
3. Keep cross‑service foreign keys explicit; document them in code comments.
4. Prefer UUID primary keys (already default in `EnvoxyBase`).
5. For analytics / heavy reporting, replicate to a warehouse instead of joining across unrelated domains.

## Pattern: Shared Read Models
A dedicated service creates summary / projection tables. Others read them via direct connector (no ORM ownership) to avoid duplicate write logic.

## Validation
Use `validate_models` (if you encode JSON model specs) or custom tests ensuring schemas align with expectations.
