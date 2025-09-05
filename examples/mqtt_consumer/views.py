"""Example MQTT on_event consumer.

Intended usage inside a service where `envoxy` is installed and the
framework auto-discovers view classes. Imports are commented to prevent
static analysis issues when this example is viewed standalone.

Uncomment in a real project:

    from envoxy.decorators import on, log_event
    from envoxy.views import View

"""

# placeholder stand-ins so this file parses without the actual imports in tooling contexts
class _BaseView:  # minimal shim
    pass

def on(**_k):  # no-op decorator shim
    def _d(cls):
        return cls
    return _d

def log_event(func):  # pass-through shim
    return func

View = _BaseView

@on(endpoint='/demo/devices/#', protocols=['mqtt'], server='default')
class DeviceEvents(View):
    """Example on_event MQTT view.

    Subscribe to all topics under /demo/devices/ and log incoming payloads.
    The dispatcher auto-subscribes when the framework boots and loads views.
    """

    @log_event
    def on_event(self, data, **kwargs):  # kwargs may contain endpoint/server metadata
        # Replace with domain logic (persist, transform, etc.)
        # data is already a decoded JSON object (dict)
        if kwargs:
            pass  # reference kwargs to avoid linter unused warning
        print('[DeviceEvents] received', data)
