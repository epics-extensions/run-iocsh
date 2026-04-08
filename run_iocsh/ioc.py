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

import errno
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from enum import Enum
from typing import BinaryIO, Self

log = logging.getLogger(__name__)

RE_MODULE_NOT_AVAILABLE = re.compile("Module .*? not available")
RE_CANT_OPEN = re.compile(r"[Cc]an't\s*open\s*(.*?):")
RE_DOES_NOT_EXIST = re.compile(r"File (.*) does not exist")
RE_MISSING_SHARED_LIB = re.compile(r"(lib.*): cannot open shared object file")
RE_BUILTIN_FAIL_ON: tuple[str, ...] = (r"^ERROR",)

DEFAULT_EXECUTABLE = "iocsh"
DEFAULT_EXIT_TIMEOUT = 0.0
DEFAULT_WAIT_FOR_TIMEOUT = 5.0
DEFAULT_POLL_INTERVAL = 0.1
DEFAULT_DELAY = 5.0
DEFAULT_THREAD_TIMEOUT = 5.0
DEFAULT_THREAD_JOIN_TIMEOUT = 1.0

TAIL_CHARS = 500


class RunIocshError(Exception):
    """Base class for exceptions in this module."""


class IocshStateError(RunIocshError):
    """Exception raised for programming errors (wrong state transitions)."""


class IocshAlreadyRunningError(IocshStateError):
    """Exception raised when IOC is started a second time."""


class IocshTimeoutError(RunIocshError):
    """Exception raised when a timeout occurred trying to send exit to the IOC."""


class IocshStartupError(RunIocshError):
    """Exception raised when IOC exits before the expected readiness pattern appears."""


class IocshOutputError(RunIocshError):
    """Base exception for errors detected in IOC output."""


class IocshFileNotFoundError(IocshOutputError, FileNotFoundError):
    """Exception raised when a file referenced in the startup script is not found."""


class IocshModuleNotFoundError(IocshOutputError):
    """Exception raised when the required module is not found."""


class IocshMissingSharedLibraryError(IocshOutputError):
    """Exception raised when shared library is missing."""


class IocshProcessError(IocshOutputError):
    """Exception raised when the iocsh script exits with a non null return code."""


class IocshPatternMatchError(IocshOutputError):
    """Exception raised when a fail_on pattern matches the IOC output."""


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
        fail_on: list[str] | None = None,
    ) -> None:
        self.proc = None
        self.args = args
        self.executable = executable
        if not shutil.which(self.executable):
            raise FileNotFoundError(f"No such file or directory: '{self.executable}'")
        self.timeout = timeout
        self._fail_on = fail_on
        self.state = self.state_values.INITIALIZED
        self._stdout_lines: list[str] = []
        self._stderr_lines: list[str] = []
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None

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
        if exc_type is None:
            self.check_output(fail_on=self._fail_on)

    @property
    def pid(self) -> int | None:
        """Return the subprocess PID, or None if not yet started."""
        return self.proc.pid if self.proc else None

    @property
    def stdout(self) -> str:
        """Return accumulated stdout as a single newline-joined string."""
        return "\n".join(self._stdout_lines)

    @property
    def stderr(self) -> str:
        """Return accumulated stderr as a single newline-joined string."""
        return "\n".join(self._stderr_lines)

    def is_running(self) -> bool:
        """Return True if the subprocess is still running.

        This only reflects subprocess state — it does NOT indicate that iocInit
        has completed, that records are available, or that CA/PVA is ready to
        serve clients. Use ``wait_for_output()`` for IOC readiness checks.
        """
        return self.proc is not None and self.proc.poll() is None

    def _read_stream(
        self,
        stream: BinaryIO,
        lines: list[str],
        label: str,
    ) -> None:
        for raw in iter(stream.readline, b""):
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            lines.append(line)
            log.debug("[%s] %s", label, line)

    def _join_reader_threads(self) -> None:
        if self._stdout_thread is not None:
            self._stdout_thread.join(timeout=DEFAULT_THREAD_TIMEOUT)
            if self._stdout_thread.is_alive():
                log.warning(
                    "stdout reader thread did not finish within %s s",
                    DEFAULT_THREAD_TIMEOUT,
                )
        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=DEFAULT_THREAD_TIMEOUT)
            if self._stderr_thread.is_alive():
                log.warning(
                    "stderr reader thread did not finish within %s s",
                    DEFAULT_THREAD_TIMEOUT,
                )

    def start(self) -> None:
        """Start the IOC subprocess.

        Raises:
            IocshAlreadyRunningError: If the IOC is already running.
        """
        if self.state == self.state_values.STARTED:
            raise IocshAlreadyRunningError("IOC already running")

        self.state = self.state_values.STARTED
        self._stdout_lines = []
        self._stderr_lines = []

        cmd = [str(item) for item in [self.executable, *self.args]]
        log.debug("Running: %s", " ".join(cmd))
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        self._stdout_thread = threading.Thread(
            target=self._read_stream,
            args=(self.proc.stdout, self._stdout_lines, "stdout"),
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(self.proc.stderr, self._stderr_lines, "stderr"),
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

    def exit(self) -> None:
        """Send the exit command to the running IOC."""
        if self.state != self.state_values.STARTED:
            log.warning("IOC is not running")
            return

        self.state = self.state_values.EXITED

        try:
            self.proc.stdin.write(b"exit\n")
            self.proc.stdin.flush()
            self.proc.stdin.close()
        except OSError:
            pass  # process already exited

        try:
            self.proc.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
            self._join_reader_threads()
            raise IocshTimeoutError("Failed to send exit to the IOC") from None

        self._join_reader_threads()

    def wait_for_output(
        self,
        pattern: str = "iocRun: All initialization complete",
        timeout: float = DEFAULT_WAIT_FOR_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        """Block until ``pattern`` appears in stdout or stderr.

        Returns immediately if the pattern is already present in buffered output.

        Args:
            pattern: Regex pattern to search for in combined stdout+stderr.
            timeout: Maximum seconds to wait before raising.
            poll_interval: Seconds to sleep between polls.

        Raises:
            IocshStartupError: If the IOC exits before the pattern appears.
            IocshTimeoutError: If ``timeout`` expires while the IOC is still running.
        """
        compiled = re.compile(pattern)
        deadline = time.monotonic() + timeout

        while True:
            if compiled.search(self.stdout + self.stderr):
                return

            if not self.is_running():
                if self._stdout_thread is not None:
                    self._stdout_thread.join(timeout=DEFAULT_THREAD_TIMEOUT)
                if self._stderr_thread is not None:
                    self._stderr_thread.join(timeout=DEFAULT_THREAD_TIMEOUT)
                if compiled.search(self.stdout + self.stderr):
                    return
                raise IocshStartupError(
                    f"IOC exited (rc={self.proc.returncode}) before pattern "
                    f"{pattern!r} appeared.\n"
                    f"stdout (last {TAIL_CHARS} chars):\n{self.stdout[-TAIL_CHARS:]}\n"
                    f"stderr (last {TAIL_CHARS} chars):\n{self.stderr[-TAIL_CHARS:]}"
                )

            if time.monotonic() >= deadline:
                raise IocshTimeoutError(
                    f"Timed out after {timeout}s waiting for {pattern!r}"
                )

            time.sleep(poll_interval)

    def check_output(self, fail_on: list[str] | None = None) -> None:
        """Inspect accumulated output and raise on detected errors.

        Always applies ``BUILTIN_FAIL_ON`` patterns plus the hardcoded checks
        (module not found, can't open, missing shared library, file does not
        exist, non-zero exit code).

        Args:
            fail_on: Additional regex patterns to match against combined
                stdout+stderr. Pass ``["MY:"]`` to catch ``MY:`` on top of
                the built-in checks.

        Raises:
            IocshStateError: If called before the process has exited.
            IocshPatternMatchError: If any pattern matches the output.
            IocshProcessError: If the process exited with a non-zero code.
        """
        if self.state != self.state_values.EXITED:
            raise IocshStateError("check_output() called before exit()")

        log.debug("return code: %s", self.proc.returncode)
        combined = self.stdout + self.stderr
        patterns = RE_BUILTIN_FAIL_ON + tuple(fail_on or [])
        for pattern in patterns:
            m = re.search(pattern, combined, re.MULTILINE)
            if m:
                raise IocshPatternMatchError(
                    f"Pattern {pattern!r} matched output: {m.group(0)!r}"
                )
        m = RE_MODULE_NOT_AVAILABLE.search(combined)
        if m:
            raise IocshModuleNotFoundError(m.group(0))
        m1 = RE_CANT_OPEN.search(combined)
        m2 = RE_DOES_NOT_EXIST.search(combined)
        if m1 or m2:
            filename = m1.group(1) if m1 else m2.group(1)
            raise IocshFileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), filename
            )
        m = RE_MISSING_SHARED_LIB.search(combined)
        if m:
            raise IocshMissingSharedLibraryError(
                f"Missing shared library: '{m.group(1)}'"
            )
        if self.proc.returncode != 0:
            raise IocshProcessError(
                f"Return code: {self.proc.returncode}\n{self.stderr}"
            )


def run_iocsh(
    *args: str,
    delay: float = DEFAULT_DELAY,
    timeout: float = DEFAULT_EXIT_TIMEOUT,
    executable: str = DEFAULT_EXECUTABLE,
    fail_on: list[str] | None = None,
) -> IOC:
    """Start IOC, wait for iocInit, sleep delay seconds, exit, check output.

    Returns:
        The exited ``IOC`` instance. Access ``.stdout`` and ``.stderr`` for
        output inspection after the call returns.
    """
    with IOC(*args, executable=executable, timeout=timeout, fail_on=fail_on) as ioc:
        ioc.wait_for_output()
        time.sleep(delay)
    return ioc
