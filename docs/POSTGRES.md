## PostgreSQL Usage

Envoxy provides two complementary access modes:
1. Direct connector (`pgsqlc`) for simple SQL + explicit transactions.
2. ORM layer (SQLAlchemy) with `EnvoxyBase` for rich models & migrations.

Use either or both—pick the simplest tool that fits the job.

### 1. Direct Connector
```python
from envoxy import pgsqlc

rows = pgsqlc.query("main", "select id, name from aux_products limit 5")

from datetime import datetime
with pgsqlc.transaction("main") as db:
	db.insert("aux_audit_events", {
		"id": "...uuid...",
		"action": "created",
		"created": datetime.utcnow(),
		"updated": datetime.utcnow()
	})
```
All writes must occur inside a `transaction()` context.

#### When to choose direct
* Ad‑hoc queries
* Bulk operations / performance tuning
* Reporting / ETL scripts

### 2. ORM Layer (`EnvoxyBase`)
Automatic naming & audit conventions:
* Table prefix: `aux_`
* Pluralization (`Product` -> `aux_products`)
* Injected columns: `id` (UUID), `created`, `updated`, `href`
* Index naming standardization

```python
from envoxy.db.orm import EnvoxyBase
from sqlalchemy import Column, String

class Product(EnvoxyBase):
	name = Column(String(255), nullable=False)

metadata = EnvoxyBase.metadata  # used by Alembic
```

### Sessions
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
You can run bulk loads with the direct connector and transactional entity work with the ORM in the same service. Keep cross‑mode consistency by committing ORM work before issuing connector queries that depend on it.

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

