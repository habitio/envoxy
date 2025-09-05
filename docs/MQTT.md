## MQTT Usage

High‑level publish/subscribe plus decorator‑based event classes integrated with the Envoxy dispatcher for automatic re‑subscription and structured logging.

### Publish
```python
from envoxy import mqttc
mqttc.publish('broker', '/v3/topic/channel', {"data": "value"}, no_envelope=True)
```

### Subscribe (Callback)
```python
from envoxy import mqttc

def handler(payload, **meta):
	print(payload)

mqttc.subscribe('broker', '/v3/topic/channels/#', handler)
```

### Event Class
```python
from envoxy import on
from envoxy.decorators import log_event

@on(endpoint='/v3/topic/channels/#', protocols=['mqtt'], server='broker')
class ChannelsView(View):
	@log_event
	def on_event(self, data, **kw):
		process(data)
```

### Envelope Control
* `no_envelope=True` publishes raw payload.
* Default may wrap your data with metadata (routing keys, timestamps). Keep consumer logic tolerant.

### Reconnection
The dispatcher stores topic patterns and re‑subscribes after reconnect automatically. Custom per‑subscription QoS can be added when extended.

### QoS (Pluggable)
Current abstraction targets common cases; if you require guaranteed delivery (QoS 1/2) ensure underlying configuration enables it and extend the dispatcher where needed.

### Performance Tips
* Prefer narrow wildcards over very broad `#` to reduce broker strain.
* Serialize payloads compactly (avoid large nested JSON when not required).
* Batch related emits when latency budget allows.

### Troubleshooting
| Symptom | Hint |
|---------|------|
| Messages missing | Confirm subscription pattern and broker ACLs |
| High latency | Inspect network / broker load; reduce payload size |
| Duplicate delivery | Check at‑least‑once semantics; handle idempotently |

### Security
Use TLS (`mqtts://`) and per‑service credentials. Never embed secrets in code; load from environment.

