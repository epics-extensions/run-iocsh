"""Standalone utilities for run-iocsh."""

# Copyright (c) 2024 European Spallation Source ERIC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
