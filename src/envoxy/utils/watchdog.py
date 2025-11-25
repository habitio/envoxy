"""Watchdog helper for sending systemd/uwsgi keep-alive notifications."""

# ruff: noqa: E722
import logging
import threading
import time
import traceback
import os

import requests

try:
    import uwsgi
except ImportError:
    pass

from ..utils.config import Config
from ..utils.logs import Log as log

logger = logging.getLogger(__name__)

# Prefer cysystemd (binary wheels available). Fall back to systemd if
# cysystemd is not installed. If neither is available, operate
# without systemd notifications (graceful degradation).
try:
    from cysystemd.daemon import notify as _notify_real
    def notify(msg):
        # When NOTIFY_SOCKET is not set, cysystemd.notify is effectively a no-op.
        # Log the attempted notification so watchdog activity is visible in logs
        # during testing even when systemd socket is not present.
        if os.environ.get('NOTIFY_SOCKET') is None:
            # Use WARNING so the message is visible in typical journal logs
            log.warning(f"[Watchdog] notify() called but NOTIFY_SOCKET unset: {msg}")
        return _notify_real(msg)
except ImportError:
    try:
        from systemd.daemon import notify as _notify_real
        def notify(msg):
            if os.environ.get('NOTIFY_SOCKET') is None:
                # Use WARNING so the message is visible in typical journal logs
                log.warning(f"[Watchdog] notify() called but NOTIFY_SOCKET unset: {msg}")
            return _notify_real(msg)
    except ImportError:

        def notify(msg):
            # No systemd bindings available — log at error level so it's obvious.
            log.error(
                f"[{log.style.apply('Watchdog', log.style.RED_FG)}] systemd not available, cannot send notification: {msg}"
            )


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
            # Guard against multiple starts in the same process
            # Check if a watchdog thread already exists
            for thread in threading.enumerate():
                if thread.name == "watchdog" and thread.is_alive():
                    log.verbose(
                        f"[{log.style.apply('Watchdog', log.style.YELLOW_FG)}] watchdog thread already running in this process (pid={os.getpid()}), skipping duplicate start"
                    )
                    return
            
            try:
                self.thread = threading.Thread(
                    target=self.send_notification, name="watchdog"
                )
                self.thread.daemon = True
                self.thread.start()
                # Log at WARNING so the message is visible in systemd journal
                # and we can confirm the watchdog thread actually started in production.
                try:
                    log.warning(
                        f"[{log.style.apply('Watchdog', log.style.GREEN_FG)}] watchdog thread started (name={self.thread.name}, ident={self.thread.ident}, pid={os.getpid()})"
                    )
                except Exception:
                    # Best-effort logging; don't prevent startup if style/ident access fails
                    log.warning(
                        f"[Watchdog] watchdog thread started (pid={os.getpid()})"
                    )
                # Send an immediate notify to satisfy systemd watchdog timers
                # so the service doesn't get killed before the first periodic notify
                try:
                    notify("WATCHDOG=1")
                    log.verbose(
                        f"[{log.style.apply('Watchdog', log.style.GREEN_FG)}] initial WATCHDOG=1 sent on start"
                    )
                except Exception:
                    log.warning(
                        f"[{log.style.apply('Watchdog', log.style.YELLOW_FG)}] initial WATCHDOG notify failed: {traceback.format_exc(limit=2)}"
                    )
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
                
                if not main_thread_alive:
                    log.warning(
                        f"[{log.style.apply('Watchdog', log.style.RED_FG)}] Main thread is dead, stopping watchdog"
                    )
                    break
                
                # Check health: either last_event_ms is recent OR HTTP test passes
                is_healthy = False
                
                # Check 1: uwsgi last_event_ms
                try:
                    if "last_event_ms" in uwsgi.opt:
                        elapsed = time.time() - uwsgi.opt["last_event_ms"]
                        if elapsed <= self.interval:
                            is_healthy = True
                            log.verbose(
                                f"[{log.style.apply('Watchdog', log.style.GREEN_FG)}] uwsgi heartbeat OK (last event {elapsed:.1f}s ago)"
                            )
                except (KeyError, TypeError, NameError):
                    pass
                
                # Check 2: HTTP health test (fallback)
                if not is_healthy:
                    is_healthy = self._test_http()
                
                # Always send notification (graceful degradation)
                # Track failures but give a few retries before stopping
                if is_healthy:
                    notify("WATCHDOG=1")
                    log.verbose(
                        f"[{log.style.apply('OK', log.style.GREEN_FG)}] Watchdog sent successfully"
                    )
                    if hasattr(self, '_failure_count'):
                        self._failure_count = 0
                else:
                    # Track consecutive failures
                    self._failure_count = getattr(self, '_failure_count', 0) + 1
                    
                    if self._failure_count <= 3:
                        # Still send notification for first 3 failures (transient issues)
                        notify("WATCHDOG=1")
                        log.warning(
                            f"[{log.style.apply('Watchdog', log.style.YELLOW_FG)}] Health check failed ({self._failure_count}/3) but still notifying systemd"
                        )
                    else:
                        # After 3 consecutive failures, stop sending (let systemd restart)
                        log.error(
                            f"[{log.style.apply('Watchdog', log.style.RED_FG)}] Health check failed {self._failure_count} times, stopping notifications (systemd will restart service)"
                        )
                        break

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
        """Test HTTP server health using the internal /_health endpoint.
        
        This method attempts to GET the /_health endpoint which is automatically
        registered by the framework for watchdog health checks. This endpoint is
        preferred over hitting the base URL because it:
        - Returns 200 OK (not 404)
        - Doesn't interfere with user routes
        - Is specifically designed for health checks
        """
        try:
            _host = Config.get("boot")[0].get("http", {}).get("bind", None)

            if _host:
                # Parse the bind address to construct the health endpoint URL
                # bind format can be "http://localhost:8080" or "localhost:8080" or ":8080"
                if _host.startswith("http://") or _host.startswith("https://"):
                    health_url = f"{_host}/_health"
                elif _host.startswith(":"):
                    health_url = f"http://localhost{_host}/_health"
                else:
                    health_url = f"http://{_host}/_health"
                
                log.verbose(f"> watchdog event on {health_url}")
                # Add a short timeout to avoid hanging if the host is unresponsive.
                response = requests.get(health_url, timeout=5)
                
                # Check for 200 OK response
                if response.status_code == 200:
                    uwsgi.opt["last_event_ms"] = time.time()
                    log.verbose(
                        f"[{log.style.apply('Watchdog', log.style.GREEN_FG)}] HTTP health check passed (/_health returned 200)"
                    )
                    return True
                else:
                    log.warning(
                        f"[{log.style.apply('Watchdog', log.style.YELLOW_FG)}] HTTP health check returned {response.status_code} (expected 200)"
                    )

        except (KeyError, requests.RequestException) as e:
            log.error(
                f"[{log.style.apply('Watchdog', log.style.RED_FG)}] HTTP watchdog test failed: {e}"
            )

        return False
