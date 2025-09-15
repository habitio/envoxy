## PostgreSQL Usage

Envoxy provides two complementary access modes:
1. Direct connector (`pgsqlc`) for simple, read-only SQL and explicit transactions when needed.
2. ORM layer (SQLAlchemy) with `EnvoxyBase` for all writes plus rich models & migrations.

Prefer the ORM for inserts and other entity writes. Use the direct connector for reads and maintenance queries.

### 1. Direct Connector (reads)
```python
from envoxy import pgsqlc

# Simple read
rows = pgsqlc.query("main", "select id, name from aux_products limit 5")

# If you need a transactional context for multiple reads or maintenance
with pgsqlc.transaction("main") as db:
	# run read queries using db.query(...) as needed
	pass
```

#### When to choose direct
* Ad‑hoc queries and reporting
* Bulk reads / performance tuning
* Operational maintenance where no inserts are required

### 2. ORM Layer (`EnvoxyBase`)
Automatic naming & audit conventions:
* Table prefix: `aux_<namespace>_` (derived automatically from `ENVOXY_SERVICE_NAMESPACE`)
* Pluralization (`Product` -> `aux_<namespace>_products`)
* Injected columns: `id` (UUID), `created`, `updated`, `href`
* Index naming standardization

```python
from envoxy.db.orm import EnvoxyBase
from sqlalchemy import Column, String

class Product(EnvoxyBase):
	name = Column(String(255), nullable=False)

metadata = EnvoxyBase.metadata  # used by Alembic
```

### Sessions (writes via ORM)
```python
from envoxy.db.orm.session import session_scope

with session_scope() as s:
	s.add(Product(name="Widget"))
```

### Migrations
```bash
envoxy-alembic revision -m "add product" --autogenerate
envoxy-alembic upgrade head
```

### Mixing Modes
You can combine the direct connector for reads with ORM writes in the same service. Commit ORM work before issuing connector queries that depend on it.

### Error Handling Tips
| Issue | Mitigation |
|-------|-----------|
| Long transactions | Split into smaller batches |
| Deadlocks | Order writes consistently; add retries around serialization failures |
| Slow queries | Use `EXPLAIN`, create appropriate indexes (framework handles naming) |

### Performance Notes
* Use parameterized queries for repeated direct executions.
* Consider `session.execute(text("..."), params)` for hybrid raw SQL within ORM transactions.
* Avoid loading large result sets fully—stream or paginate.

### Checklist Before Production
* All tables created via migrations
* Indexes present for key predicates
* Foreign keys validated (if used across services)
* Connection limits sized per workload

