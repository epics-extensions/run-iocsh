"""Class for running an IOC and capturing output."""

import contextlib
import errno
import logging
import os
import re
import shutil
import signal
import subprocess
import threading
import time
import weakref
from collections.abc import Sequence
from enum import Enum, auto
from typing import BinaryIO, Self

from run_iocsh.exceptions import (
    IocshAlreadyRunningError,
    IocshFileNotFoundError,
    IocshMissingSharedLibraryError,
    IocshModuleNotFoundError,
    IocshPatternMatchError,
    IocshProcessError,
    IocshStartupError,
    IocshStateError,
    IocshTimeoutError,
)
from run_iocsh.utils import DEFAULT_POLL_INTERVAL

log = logging.getLogger(__name__)


RE_ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")
RE_MODULE_NOT_AVAILABLE = re.compile(r"Error loading module:? (\S+?)\.?$", re.MULTILINE)
RE_CANT_OPEN = re.compile(r"[Cc]an't\s*open\s*(.*?):")
RE_DOES_NOT_EXIST = re.compile(r"File (.*) does not exist")
RE_MISSING_SHARED_LIB = re.compile(r"(lib.*): cannot open shared object file")
RE_BUILTIN_FAIL_ON = r"^ERROR"
DEFAULT_FAIL_ON: tuple[str, ...] = (RE_BUILTIN_FAIL_ON,)

DEFAULT_EXECUTABLE = "iocsh"
DEFAULT_INIT_PATTERN = "iocRun: All initialization complete"
DEFAULT_EXIT_TIMEOUT: float | None = 10.0
DEFAULT_INIT_TIMEOUT: float | None = 5.0
DEFAULT_DELAY = 5.0
DEFAULT_THREAD_TIMEOUT = 5.0
# Seconds an unresponsive IOC gets to shut down on SIGINT before it is killed.
TERMINATE_GRACE = 0.5

TAIL_CHARS = 500


def _drain_stream(
    stream: BinaryIO,
    sink: list[tuple[str, str]],
    label: str,
) -> None:
    """Drain ``stream`` into ``sink`` until EOF.

    Deliberately a plain function rather than a method: a thread target holds
    its arguments for the thread's whole life, so a bound method would keep the
    IOC referenced and defeat the finalizer that kills an abandoned subprocess.
    """
    # list.append is atomic under CPython's GIL, so both reader threads can
    # append to the shared buffer while the main thread reads it. Appending from
    # both is also what puts the two streams in arrival order.
    for raw in iter(stream.readline, b""):
        decoded = raw.decode("utf-8", errors="replace").rstrip("\n")
        # EPICS colourises errlog unconditionally, even to a pipe, so the
        # escapes would otherwise defeat any pattern anchored at the start of a
        # line, such as the ^ERROR in DEFAULT_FAIL_ON.
        line = RE_ANSI_SGR.sub("", decoded)
        sink.append((label, line))
        log.debug("[%s] %s", label, line)


def _terminate_group(proc: subprocess.Popen, pgid: int) -> bool:
    """Stop the IOC's whole process group and report whether it was running.

    ``iocsh`` is a wrapper that spawns the real IOC (``softIocPVX``) as a child,
    so signalling only ``proc`` leaves the IOC orphaned -- still holding its CA
    and PVA ports, and holding the pipes open so the reader threads block. The
    IOC runs in its own session (``start_new_session``), which makes the wrapper
    the group leader, so ``pgid`` can be signalled directly. Signalling the group
    rather than the wrapper reaches the IOC even after the wrapper has exited.

    SIGINT first, the way Ctrl-C stops an interactive IOC: it lets EPICS run its
    atexit hooks and release resources. If the wrapper does not exit within the
    grace period, escalate to SIGKILL. The wrapper can also exit on SIGINT while
    a child ignores it, so once the wrapper is gone SIGKILL the group anyway to
    reap any child that outlived it.

    That final SIGKILL runs after the wrapper -- the group leader -- has been
    reaped. With no members left the kernel may reuse the pgid, so a stray group
    could in principle receive it. The window is microseconds wide and needs
    PID-space wraparound to matter, so it is named and accepted rather than
    guarded.

    Returns True if the group was still running when it was signalled, so the
    caller can attribute the return code to us rather than to the IOC's own exit.
    """
    signalled = False
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pgid, signal.SIGINT)
        signalled = True
    try:
        proc.wait(timeout=TERMINATE_GRACE)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pgid, signal.SIGKILL)
        proc.wait()
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pgid, signal.SIGKILL)
    return signalled


def _kill_orphan(proc: subprocess.Popen, pgid: int) -> None:
    """Stop the process group of an IOC discarded without calling ``exit()``."""
    if proc.returncode is not None:
        # exit() or kill() already reaped it, so its pgid may have been reused;
        # do not signal it. Only an unreaped wrapper still owns a live group.
        return
    log.warning("IOC subprocess %s was discarded without exit(); stopping it", proc.pid)
    _terminate_group(proc, pgid)


class IOC:
    """Class to wrap IOC process.

    Not thread-safe: all public methods should be called from a single thread.
    Internal reader threads are managed by the class itself.
    """

    class State(Enum):
        """Lifecycle state of the IOC subprocess."""

        INITIALIZED = auto()
        STARTED = auto()
        EXITED = auto()

    def __init__(
        self,
        *args: str,
        executable: str = DEFAULT_EXECUTABLE,
        exit_timeout: float | None = DEFAULT_EXIT_TIMEOUT,
        fail_on: Sequence[str] = DEFAULT_FAIL_ON,
    ) -> None:
        self.proc = None
        self.args = args
        self.executable = executable
        if not shutil.which(self.executable):
            raise FileNotFoundError(f"No such file or directory: '{self.executable}'")
        self.exit_timeout = exit_timeout
        self._fail_on = fail_on
        self.state = IOC.State.INITIALIZED
        self._lines: list[tuple[str, str]] = []
        self._finalizer: weakref.finalize | None = None
        self._pgid: int | None = None
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

    def _joined(self, label: str | None = None) -> str:
        return "\n".join(
            line for stream, line in self._lines if label in (None, stream)
        )

    @property
    def stdout(self) -> str:
        """Return accumulated stdout as a single newline-joined string."""
        return self._joined("stdout")

    @property
    def stderr(self) -> str:
        """Return accumulated stderr as a single newline-joined string."""
        return self._joined("stderr")

    @property
    def output(self) -> str:
        """Return stdout and stderr interleaved, in the order the lines arrived.

        Prefer this over ``stdout + stderr`` for matching: concatenating the two
        glues the last stdout line onto the first stderr line, and orders every
        stderr line after every stdout line regardless of when it was emitted.

        Ordering across the two pipes is approximate — it reflects the order the
        reader threads observed lines, which buffering can perturb. Order within
        a single stream is exact.
        """
        return self._joined()

    def is_running(self) -> bool:
        """Return True if the subprocess is still running.

        This only reflects subprocess state — it does NOT indicate that iocInit
        has completed, that records are available, or that CA/PVA is ready to
        serve clients. Use ``wait_for_output()`` for IOC readiness checks.
        """
        return self.proc is not None and self.proc.poll() is None

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
            IocshStateError: If the IOC has already exited.
        """
        if self.state is IOC.State.STARTED:
            raise IocshAlreadyRunningError("IOC already running")
        if self.state is IOC.State.EXITED:
            raise IocshStateError(
                "IOC has already exited; create a new instance to run again"
            )

        self.state = IOC.State.STARTED
        self._lines = []

        cmd = [str(item) for item in [self.executable, *self.args]]
        log.debug("Running: %s", " ".join(cmd))
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Own session, so teardown can signal the whole group -- the wrapper
            # and the softIocPVX it spawns -- without also hitting this process.
            start_new_session=True,
        )
        # start_new_session makes the wrapper the group leader, so its pgid is
        # its pid. Capture it so teardown can signal the group even once the
        # wrapper itself has exited.
        self._pgid = self.proc.pid

        # Kill the subprocess if this IOC is ever dropped without exit() -- a
        # fixture that raises between start() and yield never reaches its
        # teardown, and a leaked IOC keeps holding its ports.
        self._finalizer = weakref.finalize(self, _kill_orphan, self.proc, self._pgid)

        self._stdout_thread = threading.Thread(
            target=_drain_stream,
            args=(self.proc.stdout, self._lines, "stdout"),
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=_drain_stream,
            args=(self.proc.stderr, self._lines, "stderr"),
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

    def exit(self) -> None:
        """Send the exit command to the running IOC."""
        if self.state is not IOC.State.STARTED:
            log.warning("IOC is not running")
            return

        self.state = IOC.State.EXITED

        with contextlib.suppress(OSError):
            self.proc.stdin.write(b"exit\n")
            self.proc.stdin.flush()
        with contextlib.suppress(OSError):
            self.proc.stdin.close()

        try:
            self.proc.wait(timeout=self.exit_timeout)
        except subprocess.TimeoutExpired:
            _terminate_group(self.proc, self._pgid)
            raise IocshTimeoutError("Failed to send exit to the IOC") from None
        finally:
            self._join_reader_threads()

    def wait_for_output(
        self,
        pattern: str = DEFAULT_INIT_PATTERN,
        timeout: float | None = DEFAULT_INIT_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        """Block until ``pattern`` appears in stdout or stderr.

        Returns immediately if the pattern is already present in buffered output.

        Args:
            pattern: Regex pattern to search for in ``output``.
            timeout: Maximum seconds to wait. ``None`` waits forever, as it does
                throughout the standard library. ``0`` checks the buffered
                output once and never blocks.
            poll_interval: Seconds to sleep between polls.

        Raises:
            IocshStateError: If called before the process has started.
            IocshStartupError: If the IOC exits before the pattern appears.
            IocshTimeoutError: If ``timeout`` expires while the IOC is still running.
        """
        if self.state is not IOC.State.STARTED:
            raise IocshStateError("wait_for_output() called before start()")

        # MULTILINE so ^ anchors at the start of any line, matching how fail_on
        # is applied -- readiness and errors arrive mid-stream, never at offset 0.
        compiled = re.compile(pattern, re.MULTILINE)
        deadline = None if timeout is None else time.monotonic() + timeout

        while True:
            if compiled.search(self.output):
                return

            if not self.is_running():
                self._join_reader_threads()
                if compiled.search(self.output):
                    return
                # The IOC died before the pattern appeared. If the output names
                # a cause, raise that; otherwise fall through to the generic
                # startup error.
                self._raise_for_reported_error()
                raise IocshStartupError(
                    f"IOC exited (rc={self.proc.returncode}) before pattern "
                    f"{pattern!r} appeared.\n"
                    f"output (last {TAIL_CHARS} chars):\n{self.output[-TAIL_CHARS:]}"
                )

            if deadline is not None and time.monotonic() >= deadline:
                raise IocshTimeoutError(
                    f"Timed out after {timeout}s waiting for {pattern!r}"
                )

            time.sleep(poll_interval)

    def check_output(
        self,
        *,
        fail_on: Sequence[str] = DEFAULT_FAIL_ON,
    ) -> None:
        """Inspect accumulated output and raise on detected errors.

        By default applies the ``DEFAULT_FAIL_ON`` patterns (``^ERROR``) plus
        the hardcoded checks (module not found, can't open, missing shared
        library, file does not exist, non-zero exit code).

        Args:
            fail_on: Regex patterns to match against ``output``.
                Replaces ``DEFAULT_FAIL_ON`` entirely — pass
                ``(*DEFAULT_FAIL_ON, "MY:")`` to extend rather than replace.
                Pass ``()`` to disable pattern checks altogether.

        Raises:
            IocshStateError: If called before the process has exited.
            IocshPatternMatchError: If any pattern matches the output.
            IocshModuleNotFoundError: If a module failed to load.
            IocshFileNotFoundError: If a file could not be opened or does not exist.
            IocshMissingSharedLibraryError: If a required shared library is missing.
            IocshProcessError: If the process exited with a non-zero code.
        """
        if self.state is not IOC.State.EXITED:
            raise IocshStateError("check_output() called before exit()")

        log.debug("return code: %s", self.proc.returncode)
        for pattern in fail_on:
            m = re.search(pattern, self.output, re.MULTILINE)
            if m:
                raise IocshPatternMatchError(
                    f"Pattern {pattern!r} matched output: {m.group(0)!r}"
                )
        self._raise_for_reported_error()
        if self.proc.returncode != 0:
            raise IocshProcessError(
                f"Return code: {self.proc.returncode}\n{self.stderr}"
            )

    def _raise_for_reported_error(self) -> None:
        """Raise a typed error if the output names a cause we recognise.

        Returns quietly when nothing matches, so callers stay responsible for
        deciding what an unexplained failure means.
        """
        combined = self.output
        m = RE_MODULE_NOT_AVAILABLE.search(combined)
        if m:
            raise IocshModuleNotFoundError(f"Error loading module: {m.group(1)}")
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


def run_iocsh(  # noqa: PLR0913 - a convenience wrapper over the whole sequence;
    # every argument names a distinct phase and all are keyword-only.
    *args: str,
    delay: float = DEFAULT_DELAY,
    exit_timeout: float | None = DEFAULT_EXIT_TIMEOUT,
    init_timeout: float | None = DEFAULT_INIT_TIMEOUT,
    pattern: str = DEFAULT_INIT_PATTERN,
    executable: str = DEFAULT_EXECUTABLE,
    fail_on: Sequence[str] = DEFAULT_FAIL_ON,
) -> IOC:
    """Start IOC, wait for ``pattern``, sleep delay seconds, exit, check output.

    Args:
        args: Arguments passed to the IOC executable.
        delay: Seconds to keep the IOC running once it is ready.
        exit_timeout: Seconds to wait for the IOC to exit after being told to
            exit. ``None`` waits forever.
        init_timeout: Seconds to wait for ``pattern`` to appear. ``None`` waits
            forever.
        pattern: Regex to wait for before considering the IOC ready.
        executable: IOC executable to run.
        fail_on: Regex patterns that make ``check_output`` raise.

    Returns:
        The exited ``IOC`` instance. Access ``.output``, ``.stdout`` and
        ``.stderr`` for inspection after the call returns.
    """
    with IOC(
        *args,
        executable=executable,
        exit_timeout=exit_timeout,
        fail_on=fail_on,
    ) as ioc:
        ioc.wait_for_output(pattern=pattern, timeout=init_timeout)
        time.sleep(delay)
    return ioc
