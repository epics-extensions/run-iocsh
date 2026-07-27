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
from collections.abc import Callable, Iterator, Sequence
from enum import Enum, auto
from typing import BinaryIO, Self

from run_iocsh.exceptions import (
    IocshAlreadyRunningError,
    IocshExitedError,
    IocshFileNotFoundError,
    IocshMissingSharedLibraryError,
    IocshModuleNotFoundError,
    IocshPatternMatchError,
    IocshProcessError,
    IocshStartupError,
    IocshStateError,
    IocshTimeoutError,
    RunIocshError,
)
from run_iocsh.utils import DEFAULT_POLL_INTERVAL

log = logging.getLogger(__name__)


RE_ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")
RE_MODULE_NOT_AVAILABLE = re.compile(r"Error loading module:? (\S+?)\.?$", re.MULTILINE)
RE_CANT_OPEN = re.compile(r"[Cc]an't\s*open\s*(.*?):")
RE_DOES_NOT_EXIST = re.compile(r"File (.*) does not exist")
RE_MISSING_SHARED_LIB = re.compile(r"(lib.*): cannot open shared object file")
RE_MISSING_DYLIB = re.compile(r"dlopen\((lib[^,)]+)[^)]*\): tried:")
RE_BUILTIN_FAIL_ON = r"^ERROR"
DEFAULT_FAIL_ON: tuple[str, ...] = (RE_BUILTIN_FAIL_ON,)

DEFAULT_EXECUTABLE = "iocsh"
DEFAULT_INIT_PATTERN = "iocRun: All initialization complete"
DEFAULT_EXIT_TIMEOUT: float | None = 10.0
DEFAULT_INIT_TIMEOUT: float | None = 5.0
DEFAULT_SETTLE = 0.0
DEFAULT_THREAD_TIMEOUT = 5.0
# Seconds an unresponsive IOC gets to shut down on SIGINT before it is killed.
TERMINATE_GRACE = 0.5

TAIL_CHARS = 500

# A detector inspects captured output and raises if it recognises a failure.
# Returning without raising means it found nothing.
Detector = Callable[[str], None]


def detect_module_not_found(output: str) -> None:
    """Raise if require reports that a module failed to load."""
    m = RE_MODULE_NOT_AVAILABLE.search(output)
    if m:
        raise IocshModuleNotFoundError(f"Error loading module: {m.group(1)}")


def detect_file_not_found(output: str) -> None:
    """Raise if the IOC shell reports a file it could not open."""
    m1 = RE_CANT_OPEN.search(output)
    m2 = RE_DOES_NOT_EXIST.search(output)
    if m1 or m2:
        filename = m1.group(1) if m1 else m2.group(1)
        raise IocshFileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filename)


def detect_missing_shared_library(output: str) -> None:
    """Raise if the dynamic linker reports a library it could not open.

    glibc and dyld report this differently: glibc prints "cannot open shared
    object file" for a ``.so``, while dyld lists every path it tried for a
    ``.dylib``. Both forms are matched.
    """
    m = RE_MISSING_SHARED_LIB.search(output) or RE_MISSING_DYLIB.search(output)
    if m:
        raise IocshMissingSharedLibraryError(f"Missing shared library: '{m.group(1)}'")


#: Detectors applied unless a caller replaces them.
#:
#: Each matches text emitted upstream, not by this library: the module-load and
#: file-not-found strings come from require's IOC shell, the shared-library
#: string from the platform's dynamic linker. Upstream has changed all of it
#: before without warning. Replace this set for an IOC that is not require-based,
#: or for a platform whose messages differ.
DEFAULT_DETECTORS: tuple[Detector, ...] = (
    detect_module_not_found,
    detect_file_not_found,
    detect_missing_shared_library,
)


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

        CREATED = auto()
        STARTED = auto()
        EXITED = auto()

    def __init__(
        self,
        *args: str,
        executable: str = DEFAULT_EXECUTABLE,
        exit_timeout: float | None = DEFAULT_EXIT_TIMEOUT,
        fail_on: Sequence[str] = DEFAULT_FAIL_ON,
        detectors: Sequence[Detector] = DEFAULT_DETECTORS,
    ) -> None:
        self.proc = None
        self.args = args
        self.executable = executable
        if not shutil.which(self.executable):
            raise FileNotFoundError(f"No such file or directory: '{self.executable}'")
        self.exit_timeout = exit_timeout
        self._fail_on = fail_on
        self._detectors = detectors
        self.state = IOC.State.CREATED
        self._killed = False
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
        if exc_type is not None:
            # The with-block body already failed. An exception raised here would
            # replace that one, reporting a symptom of the failure instead of its
            # cause -- an IOC that never became ready also tends not to exit.
            try:
                self.exit()
            except RunIocshError:
                log.warning("exit() failed while handling an error", exc_info=True)
            return
        try:
            self.exit()
        except IocshTimeoutError:
            # The IOC ignored exit. If its output shows a cause, a logged error
            # it never recovered from, report that rather than the timeout it led
            # to. Only the output checks apply, not the return code: exit()
            # killed the process, so its code reflects the signal.
            self._raise_for_matched_pattern(self._fail_on)
            self._raise_for_reported_error(self._detectors)
            raise
        self.check_output()

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
        self._killed = False
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
        """Send the exit command to the running IOC and wait for it to exit.

        Raises:
            IocshTimeoutError: If the IOC does not exit within ``exit_timeout``.
                It is killed first, so the process is always reaped.
        """
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
            self._killed = _terminate_group(self.proc, self._pgid)
            raise IocshTimeoutError("Failed to send exit to the IOC") from None
        finally:
            self._join_reader_threads()

    def kill(self) -> None:
        """Kill the IOC without asking it to exit gracefully.

        For an IOC that will not exit on command -- one that deadlocks during
        asInit and never reaches a shell that reads stdin -- ``exit()`` can only
        time out. ``kill()`` stops it outright and, unlike ``exit()``, does not
        raise. Captured output stays available, and ``check_output()`` can run
        afterwards: when kill() stopped a running process the return code is the
        kill signal and is not counted as a failure, so the ``fail_on`` and
        detector checks still apply. An IOC that had already exited on its own
        keeps its return code, which check_output() still checks.
        """
        if self.state is not IOC.State.STARTED:
            log.warning("IOC is not running")
            return

        self._killed = _terminate_group(self.proc, self._pgid)
        self._join_reader_threads()
        self.state = IOC.State.EXITED

    @classmethod
    @contextlib.contextmanager
    def ready(  # noqa: PLR0913 - mirrors run_iocsh; each argument names a phase.
        cls,
        *args: str,
        pattern: str = DEFAULT_INIT_PATTERN,
        init_timeout: float | None = DEFAULT_INIT_TIMEOUT,
        executable: str = DEFAULT_EXECUTABLE,
        exit_timeout: float | None = DEFAULT_EXIT_TIMEOUT,
        fail_on: Sequence[str] = DEFAULT_FAIL_ON,
        detectors: Sequence[Detector] = DEFAULT_DETECTORS,
    ) -> Iterator[Self]:
        """Start an IOC, block until it is ready, and yield it still running.

        Constructs the IOC, starts it, waits until it is ready, and yields it
        still running for the caller to use over CA or PVA. Leaving the block
        exits the IOC and checks its output, the same contract as
        ``with IOC(...)``. Use it instead of ``run_iocsh()`` when a test needs
        the IOC to stay up. If the IOC never becomes ready, that is raised
        before the yield -- as the recognised cause where a detector matches,
        else a startup error.

        Args:
            args: Arguments passed to the IOC executable.
            pattern: Regex to wait for before yielding, as in ``wait_for_output``.
            init_timeout: Seconds to wait for ``pattern``. ``None`` waits forever.
            executable: IOC executable to run.
            exit_timeout: Seconds to wait for the IOC to exit on block exit.
            fail_on: Regex patterns that make the exit-time check raise.
            detectors: Callables that recognise a failure in the output.

        Yields:
            The running ``IOC`` instance, ready for interaction.
        """
        with cls(
            *args,
            executable=executable,
            exit_timeout=exit_timeout,
            fail_on=fail_on,
            detectors=detectors,
        ) as ioc:
            ioc.wait_for_output(pattern=pattern, timeout=init_timeout)
            yield ioc

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
            IocshTimeoutError: If ``timeout`` expires while the IOC is still
                running. For the readiness pattern the message names
                ``wait_for_init=False``, since an IOC that never reaches
                iocInit cannot pass this wait.
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
                self._raise_for_reported_error(self._detectors)
                raise IocshStartupError(
                    f"IOC exited (rc={self.proc.returncode}) before pattern "
                    f"{pattern!r} appeared.\n"
                    f"output (last {TAIL_CHARS} chars):\n{self.output[-TAIL_CHARS:]}"
                )

            if deadline is not None and time.monotonic() >= deadline:
                # The liveness check above ran this same iteration, so what is
                # missing is the line, not the process.
                hint = " The IOC is still running."
                if pattern == DEFAULT_INIT_PATTERN:
                    # An IOC started with require's --no-init, or deadlocked in
                    # asInit, never reaches iocInit and can only time out here.
                    hint += (
                        " Pass wait_for_init=False (--no-wait-for-init) for an"
                        " IOC that does not reach iocInit."
                    )
                raise IocshTimeoutError(
                    f"Timed out after {timeout}s waiting for {pattern!r}."
                    f"{hint}\n"
                    f"output (last {TAIL_CHARS} chars):\n{self.output[-TAIL_CHARS:]}"
                )

            time.sleep(poll_interval)

    def check_output(
        self,
        *,
        fail_on: Sequence[str] | None = None,
        detectors: Sequence[Detector] | None = None,
    ) -> None:
        """Inspect accumulated output and raise on detected errors.

        By default applies the ``fail_on`` patterns and ``detectors`` this
        instance was constructed with, plus the return-code check.

        Args:
            fail_on: Regex patterns to match against ``output``. ``None`` (the
                default) uses the instance's ``fail_on``. Any value replaces it
                entirely — pass ``(*DEFAULT_FAIL_ON, "MY:")`` to extend rather
                than replace, or ``()`` to disable pattern checks altogether.
            detectors: Callables that inspect the output and raise if they
                recognise a failure. ``None`` uses the instance's ``detectors``.
                Any value replaces them entirely; pass ``()`` to rely on
                ``fail_on`` and the return code alone.

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

        if fail_on is None:
            fail_on = self._fail_on
        if detectors is None:
            detectors = self._detectors

        log.debug("return code: %s", self.proc.returncode)
        self._raise_for_matched_pattern(fail_on)
        self._raise_for_reported_error(detectors)
        if not self._killed and self.proc.returncode != 0:
            # A killed IOC's code is our signal, not the IOC's own exit; the
            # output checks above still apply, the return-code check does not.
            raise IocshProcessError(
                f"Return code: {self.proc.returncode}\n"
                f"output (last {TAIL_CHARS} chars):\n{self.output[-TAIL_CHARS:]}"
            )

    def _raise_for_matched_pattern(self, fail_on: Sequence[str]) -> None:
        """Raise if any ``fail_on`` pattern matches the output."""
        for pattern in fail_on:
            m = re.search(pattern, self.output, re.MULTILINE)
            if m:
                raise IocshPatternMatchError(
                    f"Pattern {pattern!r} matched output: {m.group(0)!r}"
                )

    def _raise_for_reported_error(self, detectors: Sequence[Detector]) -> None:
        """Raise a typed error if a detector recognises a cause in the output.

        Does nothing if no detector matches; the caller decides what an
        unrecognised failure means.
        """
        output = self.output
        for detector in detectors:
            detector(output)


def run_iocsh(  # noqa: PLR0913 - a convenience wrapper over the whole sequence;
    # every argument names a distinct phase and all are keyword-only.
    *args: str,
    settle: float = DEFAULT_SETTLE,
    exit_timeout: float | None = DEFAULT_EXIT_TIMEOUT,
    init_timeout: float | None = DEFAULT_INIT_TIMEOUT,
    pattern: str = DEFAULT_INIT_PATTERN,
    wait_for_init: bool = True,
    executable: str = DEFAULT_EXECUTABLE,
    fail_on: Sequence[str] = DEFAULT_FAIL_ON,
    detectors: Sequence[Detector] = DEFAULT_DETECTORS,
) -> IOC:
    """Start IOC, wait for ``pattern``, settle, exit, then check the output.

    Args:
        args: Arguments passed to the IOC executable.
        settle: Seconds to keep the IOC running once it is ready, before
            telling it to exit. Defaults to 0. Set it to catch an IOC that starts
            cleanly but then dies, or to give background work that leaves no trace
            in the output time to finish.
        exit_timeout: Seconds to wait for the IOC to exit after being told to
            exit. ``None`` waits forever.
        init_timeout: Seconds to wait for ``pattern`` to appear. ``None`` waits
            forever.
        pattern: Regex to wait for before considering the IOC ready. Ignored
            when ``wait_for_init`` is False.
        wait_for_init: Whether to wait for the IOC to become ready at all. Pass
            False for an IOC that never reaches iocInit -- one started with
            require's ``--no-init``, or one whose startup deadlocks during
            asInit -- where the wait could only ever time out.
        executable: IOC executable to run.
        fail_on: Regex patterns that make ``check_output`` raise.
        detectors: Callables that recognise a failure in the output.

    Returns:
        The exited ``IOC`` instance. Access ``.output``, ``.stdout`` and
        ``.stderr`` for inspection after the call returns.
    """
    with IOC(
        *args,
        executable=executable,
        exit_timeout=exit_timeout,
        fail_on=fail_on,
        detectors=detectors,
    ) as ioc:
        if wait_for_init:
            ioc.wait_for_output(pattern=pattern, timeout=init_timeout)
        time.sleep(settle)
        survived = ioc.is_running()
    # The context manager has already run check_output(), so a logged error or a
    # non-zero exit has been reported. Only a clean early exit reaches here, and
    # under a settle window that still counts as a failure: the IOC was asked to
    # stay up and did not.
    if settle and not survived:
        raise IocshExitedError(
            f"IOC exited during the {settle}s settle window (rc={ioc.proc.returncode})"
        )
    return ioc
