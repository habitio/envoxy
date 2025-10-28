"""Watchdog helper for sending systemd/uwsgi keep-alive notifications."""

# ruff: noqa: E722
import logging
import threading
import time
import traceback

import requests

try:
    import uwsgi
except ImportError:
    pass

# Prefer cysystemd (binary wheels available). Fall back to systemd if
# cysystemd is not installed. If neither is available, operate
# without systemd notifications (graceful degradation).
try:
    from cysystemd.daemon import notify
except ImportError:
    try:
        from systemd.daemon import notify
    except ImportError:

        def notify(msg):
            log.error(
                f"[{log.style.apply('Watchdog', log.style.RED_FG)}] systemd not available, cannot send notification: {msg}"
            )


from ..utils.config import Config
from ..utils.logs import Log as log

logger = logging.getLogger(__name__)


class Watchdog:
    """
    Watchdog(interval)

    A background watchdog that periodically notifies systemd (WATCHDOG=1) to indicate the
    process is alive. The watchdog runs in a separate daemon thread and performs two kinds
    of liveliness checks before sending a notification:

    - uWSGI heartbeat check: if the uWSGI option "last_event_ms" exists and the elapsed
        time since that timestamp is less than or equal to the configured interval.
    - HTTP health check: attempts an HTTP GET to the configured boot HTTP bind address
        (Config.get("boot")[0].get("http", {}).get("bind")) with a 5-second timeout. If the
        request succeeds, it updates uwsgi.opt["last_event_ms"] with the current time.

    Behavior
    - If interval is None or <= 0, the watchdog is not enabled and no thread is started.
    - If enabled, a daemon thread named "watchdog" is started which loops and waits for
        (interval - 1) seconds between checks. When a liveliness check passes, the watchdog
        attempts to import and call notify from cysystemd.daemon or systemd.daemon and send
        the "WATCHDOG=1" message.
    - The thread swallows and logs various exceptions:
        - ImportError for missing systemd bindings is caught and logged as a warning.
        - KeyError, TypeError, ValueError during checks are logged as errors.
        - Any other exceptions are logged as alerts.
    - The thread will not prevent process shutdown (daemon thread). Multiple calls to start()
        may create additional threads (the implementation only assigns the created thread to
        self.thread and does not prevent repeated starts).

    Dependencies / Side effects
    - Expects the following modules/objects to be available in the runtime:
        - threading, time, requests, traceback, uwsgi, Config, log (for logging).
        - systemd/cysystemd for notify; gracefully degrades when absent.
    - The HTTP test updates uwsgi.opt["last_event_ms"] when successful.
    - Uses log.* for verbose, error, warning, and alert messages.

    Intended usage
    - Integrate in long-running processes (e.g., uWSGI workers) that register a systemd
        watchdog. Configure `interval` to a positive number of seconds corresponding to the
        service watchdog timeout. Provides graceful degradation when systemd bindings are
        not present or when the HTTP target is unresponsive.
    """

    def __init__(self, interval):
        self.thread = None
        self.interval = interval

    def start(self):
        if self.interval is not None and self.interval > 0:
            try:
                self.thread = threading.Thread(
                    target=self.send_notification, name="watchdog"
                )
                self.thread.daemon = True
                self.thread.start()
            except (RuntimeError, OSError, threading.ThreadError):
                log.alert(
                    f"[{log.style.apply('Watchdog', log.style.RED_FG)}] Unexpected exception {traceback.format_exc(limit=5)}"
                )
        else:
            log.verbose(
                f"[{log.style.apply('Watchdog', log.style.GREEN_FG)}] not enabled, keep_alive missing or 0"
            )

    def send_notification(self):
        """
        Send periodic systemd WATCHDOG notifications while the main application appears healthy.

        This method starts a long-running loop intended to run in a background thread or worker.
        On each iteration it waits for (self.interval - 1) seconds (using a local threading.Event
        to implement the timed wait) and then, if the main thread is still alive, checks whether
        the application is healthy. Health is determined by either:
            - presence of "last_event_ms" in uwsgi.opt and the elapsed time since that event is
                less than or equal to self.interval, OR
            - the instance method self._test_http() returning a truthy value.

        If the application is considered healthy the function sends a systemd watchdog
        notification via notify("WATCHDOG=1") and writes a verbose log entry.

        Implementation notes / side effects:
            - Preferentially imports cysystemd.daemon.notify; falls back to systemd.daemon.notify.
                If neither can be imported the code degrades gracefully and logs a warning.
            - Uses global uwsgi.opt, the logging facility `log`, and may call self._test_http().
            - The local threading.Event is not returned or stored externally; termination of the
                loop therefore depends on process shutdown (or modifying the function to expose the
                event).

        Error handling:
            - Catches and logs KeyError, TypeError, ValueError as recoverable errors.
            - Catches ImportError specifically to log missing systemd support.
            - Catches and logs any other unexpected exceptions.

        Parameters:
            - self: instance providing .interval (numeric seconds) and ._test_http().

        Returns:
            - None
        """
        try:
            event = threading.Event()

            while not event.wait(self.interval - 1):
                main_thread_alive = threading.main_thread().is_alive()
                if main_thread_alive:
                    if (
                        "last_event_ms" in uwsgi.opt
                        and time.time() - uwsgi.opt["last_event_ms"] <= self.interval
                        or self._test_http()
                    ):
                        log.verbose(
                            f"[{log.style.apply('OK', log.style.GREEN_FG)}] Watchdog sent successfully"
                        )
                        notify("WATCHDOG=1")

        except (KeyError, TypeError, ValueError) as e:
            log.error(f"[{log.style.apply('Watchdog', log.style.RED_FG)}] Error {e}")
        except ImportError:
            log.warning(
                f"[{log.style.apply('Watchdog', log.style.RED_FG)}] systemd not imported {traceback.format_exc(limit=5)}"
            )
        except (NameError, AttributeError, RuntimeError, OSError) as e:
            log.alert(
                f"[{log.style.apply('Watchdog', log.style.RED_FG)}] Unexpected exception {e}\n{traceback.format_exc(limit=5)}"
            )

    def _test_http(self):
        try:
            _host = Config.get("boot")[0].get("http", {}).get("bind", None)

            if _host:
                log.verbose(f"> watchdog event on {_host}")
                # Add a short timeout to avoid hanging if the host is unresponsive.
                requests.get(_host, timeout=5)

                uwsgi.opt["last_event_ms"] = time.time()

                return True

        except (KeyError, requests.RequestException):
            log.error(
                f"[{log.style.apply('Watchdog', log.style.RED_FG)}] HTTP watchdog test failed"
            )

        return False
