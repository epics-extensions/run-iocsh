"""Standalone utilities for run-iocsh."""

import logging
import time
from collections.abc import Callable

from run_iocsh.exceptions import IocshTimeoutError

log = logging.getLogger(__name__)

DEFAULT_POLL_TIMEOUT = 5.0
DEFAULT_POLL_INTERVAL = 0.1


def wait_for(
    predicate: Callable[[], bool],
    timeout: float | None = DEFAULT_POLL_TIMEOUT,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> None:
    """Poll ``predicate`` until it returns True or ``timeout`` elapses.

    Exceptions from ``predicate`` are caught and treated as a false result
    (polling continues until timeout).

    Args:
        predicate: Callable invoked repeatedly; success when it returns True.
        timeout: Maximum seconds to wait. ``None`` waits forever, as it does
            throughout the standard library. ``0`` evaluates ``predicate`` once
            and never blocks.
        poll_interval: Seconds to sleep between polls.

    Raises:
        IocshTimeoutError: If the predicate never returns True within
            ``timeout``. Also catchable as the builtin ``TimeoutError``.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    while True:
        try:
            if predicate():
                return
        except Exception:
            log.debug("wait_for: predicate raised, treating as False", exc_info=True)
        if deadline is not None and time.monotonic() >= deadline:
            raise IocshTimeoutError(f"Timed out after {timeout}s waiting for predicate")
        time.sleep(poll_interval)
