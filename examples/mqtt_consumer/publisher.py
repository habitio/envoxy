"""Simple publisher script for the MQTT example.
Run with an environment where envoxy + its configuration is loaded.

Example:
    python -m examples.mqtt_consumer.publisher
"""

try:
    from envoxy import mqttc
except Exception:
    # fallback if running from repository root with src on PYTHONPATH
    from src.envoxy import mqttc  # type: ignore


def main():
    payload = {"device": "demo-1", "status": "online"}
    ok = mqttc.publish('default', '/demo/devices/state', payload, no_envelope=True)
    print('publish result:', ok)


if __name__ == '__main__':
    main()
