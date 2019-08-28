import threading
import traceback
import logging
import requests

from ..utils.logs import Log as log
from ..utils.config import Config


logger = logging.getLogger(__name__)


class Watchdog:

    def __init__(self, interval):
        self.thread = None
        try:
            self.interval = interval
            log.debug('[Watchdog] interval {}'.format(self.interval))
        except (KeyError, TypeError, ValueError, IndexError):
            log.info('[Watchdog] not enabled, keep_alive missing')

    def start(self, protocols_enabled):
        if self.interval is not None and self.interval > 0:
            try:
                self.thread = threading.Thread(target=self.send_notification, args=(protocols_enabled,), name="watchdog")
                self.thread.daemon = True
                self.thread.start()
            except:
                log.alert('[Watchdog] Unexpected exception {}'.format(traceback.format_exc(limit=5)))
        else:
            log.info('[Watchdog] not enabled, keep_alive missing or 0')

    def send_notification(self, protocols_enabled):
        try:
            from systemd.daemon import notify
            event = threading.Event()

            # send first notification on init
            log.debug('[Watchdog]... everything is ok {}'.format(protocols_enabled))
            notify('WATCHDOG=1')

            while not event.wait(self.interval - 1):
                main_thread_alive = threading.main_thread().is_alive()
                if main_thread_alive:

                    _http_result = self._test_http()
                    _mqtt_result = self._test_mqtt()

                    notify('WATCHDOG=1')

        except (KeyError, TypeError, ValueError):
            log.info('[Watchdog] not enabled, keep_alive missing')
        except ImportError:
            log.warning('[Watchdog] systemd not imported {}'.format(traceback.format_exc(limit=5)))
        except:
            log.alert('[Watchdog] Unexpected exception {}'.format(traceback.format_exc(limit=5)))

    def _test_http(self):
        pass

    def _test_mqtt(self):
        pass
