import logging
import threading
import time
import traceback

import requests
try:
    import uwsgi
except ImportError:
    pass

from ..utils.config import Config
from ..utils.logs import Log as log

logger = logging.getLogger(__name__)


class Watchdog:

    def __init__(self, interval):
        self.thread = None
        self.interval = interval

    def start(self):
        if self.interval is not None and self.interval > 0:
            try:
                self.thread = threading.Thread(target=self.send_notification, name="watchdog")
                self.thread.daemon = True
                self.thread.start()
            except:
                log.alert('[{}] Unexpected exception {}'.format(log.style.apply('Watchdog', log.style.RED_FG), traceback.format_exc(limit=5)))
        else:
            log.verbose('[{}] not enabled, keep_alive missing or 0'.format(log.style.apply('Watchdog', log.style.GREEN_FG)))

    def send_notification(self):
        try:
            from systemd.daemon import notify
            event = threading.Event()

            while not event.wait(self.interval - 1):
                main_thread_alive = threading.main_thread().is_alive()
                if main_thread_alive:

                    if 'last_event_ms' in uwsgi.opt and time.time() - uwsgi.opt['last_event_ms'] <= self.interval or self._test_http():
                        log.verbose('[{}] Watchdog sent successfully'.format(log.style.apply('OK', log.style.GREEN_FG)))
                        notify('WATCHDOG=1')

        except (KeyError, TypeError, ValueError) as e:
            log.error('[{}] Error {}'.format(log.style.apply('Watchdog', log.style.RED_FG), e))
        except ImportError:
            log.warning('[{}] systemd not imported {}'.format(log.style.apply('Watchdog', log.style.RED_FG), traceback.format_exc(limit=5)))
        except:
            log.alert('[{}] Unexpected exception {}'.format(log.style.apply('Watchdog', log.style.RED_FG), traceback.format_exc(limit=5)))

    def _test_http(self):

        try:

            _host = Config.get('boot')[0].get('http', {}).get('bind', None)

            if _host:

                log.verbose(f'> watchdog event on {_host}')
                requests.get(_host)

                uwsgi.opt['last_event_ms'] = time.time()

                return True

        except (KeyError, requests.RequestException):
            pass

        return False
