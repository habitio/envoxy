## CouchDB Usage

Helper utilities through `couchdbc` simplify a subset of common operations (find/select style queries & document retrieval). You can augment with direct CouchDB driver features for advanced use cases (design docs, views, attachments).

### Find
Selector suffix operators map to Mango query operators:
| Suffix | Operator |
|--------|----------|
| __gt   | $gt |
| __gte  | $gte |
| __lt   | $lt |
| __lte  | $lte |

Equality: plain key/value (`field=value`).

```python
from envoxy import couchdbc

docs = couchdbc.find(
	db="server_key.inventory",
	fields=["id", "status", "version"],
	params={"status": "active", "version__gt": 2}
)
```

### Get by ID
```python
doc = couchdbc.get("abc123", db="server_key.inventory")
```

### Paging Pattern
If the connector exposes limit/skip (future extension) you can iterate; otherwise slice results client‑side for now.

### Indexing
Define appropriate CouchDB indexes (not managed automatically here) to keep Mango queries efficient. Without an index, CouchDB may scan all documents.

### Concurrency Considerations
Use `_rev` for optimistic concurrency; stale revisions will trigger update conflicts (catch and retry with fresh state).

### When to Use CouchDB in Envoxy
* Flexible document storage where schema evolves rapidly
* Event sourcing snapshots
* Caching pre‑aggregated representations

For strong relational integrity or multi‑table joins, prefer PostgreSQL.

