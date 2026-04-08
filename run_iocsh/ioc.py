"""Class, exceptions, and utility functions for running an IOC and capturing output."""

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
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from enum import Enum
from typing import Self

log = logging.getLogger(__name__)

RE_MODULE_NOT_AVAILABLE = re.compile("Module .*? not available")
RE_CANT_OPEN = re.compile(r"[Cc]an't\s*open\s*(.*?):")
RE_DOES_NOT_EXIST = re.compile(r"File (.*) does not exist")
RE_MISSING_SHARED_LIB = re.compile(r"(lib.*): cannot open shared object file")

DEFAULT_EXECUTABLE = "iocsh"
DEFAULT_EXIT_TIMEOUT = 0.0
DEFAULT_WAIT_FOR_TIMEOUT = 5.0
DEFAULT_POLL_INTERVAL = 0.1
DEFAULT_DELAY = 5.0


class RunIocshError(Exception):
    """Base class for exceptions in this module."""


class IocshModuleNotFoundError(RunIocshError):
    """Exception raised when the required module is not found."""


class IocshProcessError(RunIocshError):
    """Exception raised when the iocsh script exits with a non null return code.

    Only raised if no error was catched (and another exception raised).
    """


class IocshTimeoutExpiredError(RunIocshError):
    """Exception raised when a timeout occurred trying to send exit to the softIOC."""


class IocshAlreadyRunningError(RunIocshError):
    """Exception raised when IOC is started a second time."""


class MissingSharedLibraryError(RunIocshError):
    """Exception raised when shared library is missing."""


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


class IOC:
    """Class to wrap IOC process."""

    state_values = Enum("state_values", "INITIALIZED STARTED EXITED")

    def __init__(
        self,
        *args: str,
        executable: str = DEFAULT_EXECUTABLE,
        timeout: float = DEFAULT_EXIT_TIMEOUT,
    ) -> None:
        self.proc = None
        self.outs = ""
        self.errs = ""
        self.args = args
        self.executable = executable
        if not shutil.which(self.executable):
            raise FileNotFoundError(f"No such file or directory: '{self.executable}'")
        self.timeout = timeout
        self.state = self.state_values.INITIALIZED

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        exc_traceback: object,
    ) -> None:
        self.exit()

    @property
    def pid(self) -> int | None:
        """Return the subprocess PID, or None if not yet started."""
        return self.proc.pid if self.proc else None

    def is_running(self) -> bool:
        """Return True if the subprocess is still running."""
        return self.proc is not None and self.proc.poll() is None

    def start(self) -> None:
        """Start the IOC subprocess.

        Raises:
            IocshAlreadyRunningError: If the IOC is already running.
        """
        if self.state == self.state_values.STARTED:
            raise IocshAlreadyRunningError("IOC already running")

        self.state = self.state_values.STARTED

        # Reset the output
        self.outs = ""
        self.errs = ""

        self._exited = False

        cmd = [str(item) for item in [self.executable, *self.args]]
        log.debug("Running: %s", " ".join(cmd))
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    def exit(self) -> None:
        """Send the exit command to the running IOC."""
        if self.state != self.state_values.STARTED:
            log.warning("IOC is not running")
            return

        self.state = self.state_values.EXITED

        try:
            outs, errs = self.proc.communicate(input=b"exit\n", timeout=self.timeout)
        except subprocess.TimeoutExpired as e:
            self.proc.kill()
            # Trying to run "outs, errs = proc.communicate()" can raise:
            # ValueError: Invalid file object: <_io.BufferedReader name=7>
            # when stdin is already closed.
            # In case of timeout, we don't care and just raise an exception
            raise IocshTimeoutExpiredError("Failed to send exit to the IOC") from e

        self.outs = outs.decode("utf-8")
        self.errs = errs.decode("utf-8")

    def check_output(self) -> None:
        """Log and check output from subprocess."""
        if self.state != self.state_values.EXITED:
            log.warning("IOC has not exited yet")
            return

        log.info(
            "========== stdout ============================\n"
            + self.outs
            + "=============================================="
        )
        log.info(
            "========== stderr ============================\n"
            + self.errs
            + "=============================================="
        )
        log.debug("return code: %s", self.proc.returncode)
        m = RE_MODULE_NOT_AVAILABLE.search(self.outs + self.errs)
        if m:
            raise IocshModuleNotFoundError(m.group(0))
        m1 = RE_CANT_OPEN.search(self.outs + self.errs)
        m2 = RE_DOES_NOT_EXIST.search(self.errs)
        if m1 or m2:
            raise FileNotFoundError(
                f"No such file or directory: '{m1.group(1) if m1 else m2.group(1)}'"
            )
        m = RE_MISSING_SHARED_LIB.search(self.outs + self.errs)
        if m:
            raise MissingSharedLibraryError(f"Missing shared library: '{m.group(1)}'")
        if self.proc.returncode != 0:
            raise IocshProcessError(f"Return code: {self.proc.returncode}\n{self.errs}")


def run_iocsh(
    *args: str,
    delay: float = DEFAULT_DELAY,
    timeout: float = DEFAULT_EXIT_TIMEOUT,
    executable: str = DEFAULT_EXECUTABLE,
) -> None:
    """Run an IOC, exit, and parse the output."""
    with IOC(*args, executable=executable, timeout=timeout) as ioc:
        time.sleep(delay)
    ioc.check_output()
