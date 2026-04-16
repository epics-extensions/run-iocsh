"""Standalone utilities for run-iocsh."""

import logging
import time
from collections.abc import Callable

from run_iocsh.ioc import DEFAULT_POLL_INTERVAL, DEFAULT_WAIT_FOR_TIMEOUT

log = logging.getLogger(__name__)


def wait_for(
    predicate: Callable[[], bool],
    timeout: float = DEFAULT_WAIT_FOR_TIMEOUT,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> None:
    """Poll ``predicate`` until it returns True or ``timeout`` elapses.

    Exceptions from ``predicate`` are caught and treated as a false result
    (polling continues until timeout).

    Args:
        predicate: Callable invoked repeatedly; success when it returns True.
        timeout: Maximum seconds to wait before giving up.
        poll_interval: Seconds to sleep between polls.

    Raises:
        TimeoutError: If the predicate never returns True within ``timeout``.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            if predicate():
                return
        except Exception:  # noqa: BLE001
            log.debug("wait_for: predicate raised, treating as False", exc_info=True)
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out after {timeout}s waiting for predicate")
        time.sleep(poll_interval)
