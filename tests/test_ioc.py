import gc
import logging
import os
import weakref
from pathlib import Path

import pytest

from run_iocsh import (
    IOC,
    IocshAlreadyRunningError,
    IocshModuleNotFoundError,
    IocshStartupError,
    IocshStateError,
    IocshTimeoutError,
    run_iocsh,
    wait_for,
)

SCRIPTS = Path(__file__).parent / "scripts"


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class TestRunIocsh:
    def test_output_logged_at_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with caplog.at_level(logging.DEBUG, logger="run_iocsh"):
            run_iocsh(executable=script, delay=0)
        assert "iocRun: All initialization complete" in caplog.text

    def test_returns_ioc_instance(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        result = run_iocsh(executable=script, delay=0)
        assert isinstance(result, IOC)

    def test_returned_ioc_output_accessible(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        result = run_iocsh(executable=script, delay=0)
        assert "iocRun: All initialization complete" in result.output

    def test_returned_ioc_is_exited(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        result = run_iocsh(executable=script, delay=0)
        assert not result.is_running()


class TestIOC:
    def test_start_exit_lifecycle(self) -> None:
        script = str(SCRIPTS / "iocsh-wait-for-exit.py")
        ioc = IOC(executable=script, timeout=5.0)
        assert not ioc.is_running()
        assert ioc.pid is None

        ioc.start()
        assert ioc.is_running()
        assert ioc.pid is not None

        ioc.exit()
        assert not ioc.is_running()

    def test_default_timeout_allows_clean_exit(self) -> None:
        script = str(SCRIPTS / "iocsh-slow-exit.py")
        ioc = IOC(executable=script)
        ioc.start()
        ioc.wait_for_output()
        ioc.exit()

    def test_start_after_exit_raises(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script, timeout=5.0) as ioc:
            pass
        with pytest.raises(IocshStateError, match="already exited"):
            ioc.start()

    def test_start_while_running_raises(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with (
            pytest.raises(IocshAlreadyRunningError) as excinfo,
            IOC(executable=script, timeout=5.0) as ioc,
        ):
            ioc.start()

        assert "IOC already running" in str(excinfo.value)

    def test_exit_while_not_running_warns(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with caplog.at_level(logging.WARNING):
            with IOC(executable=script, timeout=5.0) as ioc:
                pass
            ioc.exit()
        assert "IOC is not running" in caplog.text

    def test_check_output_before_exit_raises(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        with pytest.raises(IocshStateError):
            IOC(executable=script).check_output()


class TestOrphanCleanup:
    def test_subprocess_killed_when_ioc_is_discarded(self) -> None:
        # A pytest fixture that raises between start() and yield never reaches
        # its teardown, so exit() is never called and the IOC is left holding
        # its ports.
        script = str(SCRIPTS / "iocsh-timeout.py")
        ioc = IOC(executable=script)
        ioc.start()
        pid = ioc.pid
        assert _process_alive(pid)

        del ioc
        gc.collect()

        wait_for(lambda: not _process_alive(pid), timeout=5.0)

    def test_orphan_finalizer_reaps_the_grandchild(self) -> None:
        # A discarded IOC that spawned a grandchild must take the grandchild
        # down too, not just the wrapper.
        script = str(SCRIPTS / "iocsh-spawns-grandchild.py")
        ioc = IOC(executable=script)
        ioc.start()
        wait_for(lambda: "GRANDCHILD_PID=" in ioc.output, timeout=5.0)
        line = next(
            x for x in ioc.output.splitlines() if x.startswith("GRANDCHILD_PID=")
        )
        grandchild = int(line.split("=", 1)[1])
        assert _process_alive(grandchild)

        ioc = None
        gc.collect()

        wait_for(lambda: not _process_alive(grandchild), timeout=5.0)

    def test_finalizer_reaps_a_child_that_outlived_the_wrapper(self) -> None:
        # The wrapper exits on its own but leaves a child running. Discarding
        # the IOC must still take the child down: checking only the dead wrapper
        # would leak it.
        script = str(SCRIPTS / "iocsh-wrapper-exits-with-child.py")
        ioc = IOC(executable=script)
        ioc.start()
        wait_for(lambda: "GRANDCHILD_PID=" in ioc.output, timeout=5.0)
        line = next(
            x for x in ioc.output.splitlines() if x.startswith("GRANDCHILD_PID=")
        )
        grandchild = int(line.split("=", 1)[1])
        assert _process_alive(grandchild)

        ioc = None
        gc.collect()

        wait_for(lambda: not _process_alive(grandchild), timeout=5.0)

    def test_reader_threads_do_not_keep_the_ioc_alive(self) -> None:
        script = str(SCRIPTS / "iocsh-timeout.py")
        ioc = IOC(executable=script)
        ioc.start()
        ref = weakref.ref(ioc)

        del ioc
        gc.collect()

        assert ref() is None, "reader threads are pinning the IOC in memory"


class TestOutput:
    def test_output_includes_both_streams(self) -> None:
        script = str(SCRIPTS / "iocsh-ansi-error.py")
        with IOC(executable=script, fail_on=()) as ioc:
            ioc.wait_for_output()
        assert 'dbLoadRecords("/tmp/nosuch.db")' in ioc.output  # emitted on stdout
        assert "ERROR failed to load" in ioc.output  # emitted on stderr

    def test_output_keeps_streams_on_their_own_lines(self) -> None:
        # The last stdout line must not be glued to the first stderr line.
        script = str(SCRIPTS / "iocsh-ansi-error.py")
        with IOC(executable=script, fail_on=()) as ioc:
            ioc.wait_for_output()
        for line in ioc.output.splitlines():
            assert line in (*ioc.stdout.splitlines(), *ioc.stderr.splitlines())

    def test_output_preserves_per_stream_order(self) -> None:
        script = str(SCRIPTS / "iocsh-ansi-error.py")
        with IOC(executable=script, fail_on=()) as ioc:
            ioc.wait_for_output()
        lines = ioc.output.splitlines()
        assert lines.index('epicsEnvSet IOCSH_TOP "/tmp"') < lines.index(
            'dbLoadRecords("/tmp/nosuch.db")'
        )
        assert lines.index("Starting iocInit") < lines.index(
            "iocRun: All initialization complete"
        )

    def test_streams_remain_separately_accessible(self) -> None:
        script = str(SCRIPTS / "iocsh-ansi-error.py")
        with IOC(executable=script, fail_on=()) as ioc:
            ioc.wait_for_output()
        assert "ERROR failed to load" not in ioc.stdout
        assert 'dbLoadRecords("/tmp/nosuch.db")' not in ioc.stderr


class TestWaitForOutput:
    def test_returns_when_pattern_found(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script) as ioc:
            ioc.wait_for_output()

    def test_already_buffered_pattern_returns_immediately(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script) as ioc:
            ioc.wait_for_output(timeout=5.0)
            ioc.wait_for_output(timeout=0.0)

    def test_raises_startup_error_on_crash(self) -> None:
        script = str(SCRIPTS / "iocsh-crash.py")
        with pytest.raises(IocshStartupError, match="exited"):
            with IOC(executable=script) as ioc:
                ioc.wait_for_output(timeout=5.0)

    def test_raises_timeout_error_while_running(self) -> None:
        script = str(SCRIPTS / "iocsh-timeout.py")
        with pytest.raises(IocshTimeoutError):
            with IOC(executable=script, timeout=0.3) as ioc:
                ioc.wait_for_output(pattern="WILL_NOT_APPEAR", timeout=0.1)

    def test_output_accessible_before_exit(self) -> None:
        # Readiness arrives on stderr: EPICS sends errlog there.
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script) as ioc:
            ioc.wait_for_output()
            assert "iocRun: All initialization complete" in ioc.output
            assert "iocRun: All initialization complete" in ioc.stderr

    def test_output_accessible_after_exit(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script, timeout=5.0) as ioc:
            ioc.wait_for_output()
        assert "iocRun: All initialization complete" in ioc.output
        assert 'epicsEnvSet IOCSH_TOP "/tmp"' in ioc.stdout

    def test_stderr_accessible_after_exit(self) -> None:
        script = str(SCRIPTS / "iocsh-module-not-found.py")
        with pytest.raises(IocshModuleNotFoundError):
            with IOC(executable=script, timeout=5.0) as ioc:
                ioc.wait_for_output()
        assert "Error loading module: mock" in ioc.stderr

    def test_caplog_captures_output_at_debug(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with caplog.at_level(logging.DEBUG, logger="run_iocsh"):
            with IOC(executable=script) as ioc:
                ioc.wait_for_output()
        assert "iocRun: All initialization complete" in caplog.text

    def test_raises_state_error_before_start(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with pytest.raises(IocshStateError):
            IOC(executable=script).wait_for_output()

    def test_pattern_anchor_matches_per_line(self) -> None:
        # ^ should anchor at the start of any line, as it does for fail_on --
        # readiness and errors arrive mid-stream, never at offset 0.
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script) as ioc:
            ioc.wait_for_output(pattern="^iocRun: All initialization complete")
