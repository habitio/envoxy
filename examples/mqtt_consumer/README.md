MQTT Consumer Example
=====================

This example shows a minimal pattern for consuming MQTT events using the
framework's view/on_event mechanism plus a simple publisher.

Files
-----
- `views.py` : Defines `DeviceEvents` with an `on_event` method subscribed to `/demo/devices/#`.
- `publisher.py` : Publishes a JSON message to `/demo/devices/state`.

Usage (development)
-------------------
Ensure your service config (`mqtt_servers`) includes a `default` server key
and that the framework loads example views (add the module path to your
module discovery if needed).

Publisher run (from repo root with src on PYTHONPATH):
```bash
PYTHONPATH=src python examples/mqtt_consumer/publisher.py
```

Real project imports
--------------------
Uncomment the import lines in `views.py` and remove the shim classes when
integrating into a real service.

See also
--------
- `docs/MQTT.md` for detailed publish/subscribe and on_event examples.
