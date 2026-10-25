"""Worker composition and lifecycle. Business logic remains in owning modules."""
import logging
import signal
import time
from collections.abc import Callable
from foundation.config.settings import Settings
from foundation.database.session import Database
from modules.files.application.storage import ObjectStore

logger=logging.getLogger('arc.workers')

def resources():
    settings=Settings()
    return settings, Database(settings.database_url), ObjectStore(settings)

def run_loop(operation:Callable[[],object], *, idle_seconds:float=0.5, periodic_seconds:float|None=None)->None:
    """Process continuously or periodically; stop on SIGTERM and never log provider secrets.

    A failing operation is retried on the next interval. Adapters must be idempotent.
    """
    if idle_seconds <= 0 or (periodic_seconds is not None and periodic_seconds <= 0):
        raise ValueError('A worker interval must be positive.')
    stopping=False
    def stop(_signum, _frame):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    while not stopping:
        started=time.monotonic()
        try:
            result=operation()
        except Exception as exc:
            logger.error('worker_operation_failed error_type=%s',type(exc).__name__)
            result=False
        # Short cooperative sleep, including when the callable failed.
        cycle=(periodic_seconds if periodic_seconds is not None else (idle_seconds if not result else 0.1))
        delay=max(0.1,cycle-(time.monotonic()-started))
        until=time.monotonic()+delay
        while not stopping and time.monotonic()<until:
            time.sleep(min(0.25,max(0.0,until-time.monotonic())))
