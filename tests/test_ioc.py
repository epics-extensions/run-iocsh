import gc
import inspect
import logging
import os
import time
import weakref
from pathlib import Path

import pytest

from run_iocsh import (
    IOC,
    IocshAlreadyRunningError,
    IocshExitedError,
    IocshModuleNotFoundError,
    IocshPatternMatchError,
    IocshProcessError,
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
            run_iocsh(executable=script, settle=0)
        assert "iocRun: All initialization complete" in caplog.text

    def test_settle_defaults_to_off(self) -> None:
        # Nothing ever wanted the 5 s default: every caller passed settle=0 to
        # switch it off, paying 5 s per call for the privilege.
        assert inspect.signature(run_iocsh).parameters["settle"].default == 0

    def test_settle_keeps_the_ioc_running_when_asked(self) -> None:
        script = str(SCRIPTS / "iocsh-wait-for-exit.py")
        started = time.monotonic()
        run_iocsh(executable=script, settle=0.5)
        assert time.monotonic() - started >= 0.5

    def test_settle_fails_if_the_ioc_does_not_survive_the_window(self) -> None:
        # The point of the settle window: an IOC that becomes ready and then
        # quietly exits 0 partway through it must not be reported as a success.
        script = str(SCRIPTS / "iocsh-dies-after-ready.py")
        with pytest.raises(IocshExitedError):
            run_iocsh(executable=script, settle=3.0)

    def test_settle_zero_does_not_require_survival(self) -> None:
        # A startup script that self-exits is fine when nothing asked it to stay up.
        script = str(SCRIPTS / "iocsh-dies-after-ready.py")
        run_iocsh(executable=script, settle=0)

    def test_returns_ioc_instance(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        result = run_iocsh(executable=script, settle=0)
        assert isinstance(result, IOC)

    def test_returned_ioc_output_accessible(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        result = run_iocsh(executable=script, settle=0)
        assert "iocRun: All initialization complete" in result.output

    def test_init_timeout_and_pattern_are_passed_through(self) -> None:
        # The readiness wait was hardcoded: exit_timeout controlled the exit,
        # never the wait, which was always DEFAULT_INIT_TIMEOUT.
        script = str(SCRIPTS / "iocsh-wait-for-exit.py")
        with pytest.raises(IocshTimeoutError, match="WILL_NOT_APPEAR"):
            run_iocsh(
                executable=script,
                pattern="WILL_NOT_APPEAR",
                init_timeout=0.1,
                exit_timeout=5.0,
                settle=0,
            )

    def test_pattern_can_wait_for_something_other_than_iocinit(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        result = run_iocsh(executable=script, pattern="Starting iocInit", settle=0)
        assert "Starting iocInit" in result.output

    def test_wait_for_init_false_skips_the_readiness_wait(self) -> None:
        # An IOC started with require's --no-init never reaches iocInit, so
        # readiness never appears and waiting for it can only ever time out.
        script = str(SCRIPTS / "iocsh-no-init.py")
        result = run_iocsh(executable=script, wait_for_init=False, settle=0)
        # It never waited for readiness, so it reached exit and shut down; with
        # wait_for_init left on, the companion test shows this would time out.
        assert "Exiting e3 IOC shell" in result.output

    def test_waiting_for_init_is_still_the_default(self) -> None:
        script = str(SCRIPTS / "iocsh-no-init.py")
        with pytest.raises(IocshTimeoutError):
            run_iocsh(executable=script, settle=0, init_timeout=0.1)

    def test_returned_ioc_is_exited(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        result = run_iocsh(executable=script, settle=0)
        assert not result.is_running()


class TestIOC:
    def test_start_exit_lifecycle(self) -> None:
        script = str(SCRIPTS / "iocsh-wait-for-exit.py")
        ioc = IOC(executable=script, exit_timeout=5.0)
        assert not ioc.is_running()
        assert ioc.pid is None

        ioc.start()
        assert ioc.is_running()
        assert ioc.pid is not None

        ioc.exit()
        assert not ioc.is_running()

    def test_exit_timeout_is_named_for_its_phase(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        ioc = IOC(executable=script, exit_timeout=1.0)
        assert ioc.exit_timeout == 1.0

    def test_default_exit_timeout_is_finite(self) -> None:
        # None blocks forever, which turns an IOC that ignores exit into a hung
        # CI job rather than a failed one.
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        assert IOC(executable=script).exit_timeout is not None

    def test_default_timeout_allows_clean_exit(self) -> None:
        script = str(SCRIPTS / "iocsh-slow-exit.py")
        ioc = IOC(executable=script)
        ioc.start()
        ioc.wait_for_output()
        ioc.exit()

    def test_start_after_exit_raises(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script, exit_timeout=5.0) as ioc:
            pass
        with pytest.raises(IocshStateError, match="already exited"):
            ioc.start()

    def test_start_while_running_raises(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with (
            pytest.raises(IocshAlreadyRunningError) as excinfo,
            IOC(executable=script, exit_timeout=5.0) as ioc,
        ):
            ioc.start()

        assert "IOC already running" in str(excinfo.value)

    def test_exit_while_not_running_warns(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with caplog.at_level(logging.WARNING):
            with IOC(executable=script, exit_timeout=5.0) as ioc:
                pass
            ioc.exit()
        assert "IOC is not running" in caplog.text

    def test_check_output_before_exit_raises(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        with pytest.raises(IocshStateError):
            IOC(executable=script).check_output()

    def test_manual_check_output_uses_the_instance_fail_on(self) -> None:
        # A manually driven IOC must apply the fail_on it was configured with,
        # not the global default -- otherwise the configured policy silently
        # does not apply to the exact lifecycle the docs steer callers toward.
        script = str(SCRIPTS / "iocsh-custom-error.py")
        ioc = IOC(executable=script, fail_on=("CUSTOM_ERROR:",))
        ioc.start()
        ioc.wait_for_output()
        ioc.exit()
        with pytest.raises(IocshPatternMatchError, match="CUSTOM_ERROR:"):
            ioc.check_output()

    def test_manual_check_output_uses_the_instance_detectors(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        ioc = IOC(executable=script, detectors=())
        ioc.start()
        ioc.wait_for_output()
        ioc.exit()
        ioc.check_output()  # empty detectors: a would-be detector must not fire


class TestKill:
    def test_kill_tears_down_an_ioc_that_will_not_exit(self) -> None:
        # An IOC deadlocked in asInit never becomes ready and never reads stdin,
        # so exit() can only time out. kill() is the way to stop it, and it lets
        # the caller still inspect what the IOC managed to load.
        script = str(SCRIPTS / "iocsh-deadlocks-in-init.py")
        ioc = IOC(executable=script)
        ioc.start()
        wait_for(lambda: "iocshLoad" in ioc.output, timeout=5.0)
        ioc.kill()
        assert not ioc.is_running()
        assert "iocshLoad" in ioc.output  # loaded output survived the teardown

    def test_kill_transitions_to_exited(self) -> None:
        script = str(SCRIPTS / "iocsh-deadlocks-in-init.py")
        ioc = IOC(executable=script)
        ioc.start()
        ioc.kill()
        with pytest.raises(IocshStateError, match="already exited"):
            ioc.start()

    def test_check_output_after_kill_ignores_the_signal_return_code(self) -> None:
        # The kill signal is our doing, not the IOC's exit, so check_output must
        # not report it as a process failure -- the caller still wants to run
        # their own output checks on what the IOC managed to produce.
        script = str(SCRIPTS / "iocsh-deadlocks-in-init.py")
        ioc = IOC(executable=script)
        ioc.start()
        ioc.kill()
        ioc.check_output()

    def test_kill_after_self_exit_still_checks_the_return_code(self) -> None:
        # If the IOC already died on its own with a non-zero code, kill() is a
        # no-op and must not mask that: it only suppresses the code when it
        # actually stopped a running process.
        script = str(SCRIPTS / "iocsh-crash.py")
        ioc = IOC(executable=script)
        ioc.start()
        wait_for(lambda: not ioc.is_running(), timeout=5.0)
        ioc.kill()
        with pytest.raises(IocshProcessError):
            ioc.check_output()

    def test_exit_timeout_does_not_misreport_the_kill_signal(self) -> None:
        # exit() times out and stops the IOC with SIGINT. A caller that catches
        # the timeout and inspects output must not see that signal reported as a
        # process failure.
        script = str(SCRIPTS / "iocsh-timeout.py")
        ioc = IOC(executable=script, exit_timeout=0.3)
        ioc.start()
        ioc.wait_for_output()
        with pytest.raises(IocshTimeoutError):
            ioc.exit()
        ioc.check_output()  # must not raise IocshProcessError for the signal

    def test_kill_before_start_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with caplog.at_level(logging.WARNING):
            IOC(executable=script).kill()
        assert "IOC is not running" in caplog.text


class TestProcessGroupTeardown:
    def test_kill_reaps_the_grandchild(self) -> None:
        # iocsh spawns softIocPVX, so killing only the wrapper orphans the IOC.
        # kill() must take down the whole process group.
        script = str(SCRIPTS / "iocsh-spawns-grandchild.py")
        ioc = IOC(executable=script)
        ioc.start()
        wait_for(lambda: "GRANDCHILD_PID=" in ioc.output, timeout=5.0)
        line = next(
            x for x in ioc.output.splitlines() if x.startswith("GRANDCHILD_PID=")
        )
        grandchild = int(line.split("=", 1)[1])
        assert _process_alive(grandchild)

        ioc.kill()

        wait_for(lambda: not _process_alive(grandchild), timeout=5.0)

    def test_group_kill_reaps_a_child_that_survived_the_wrapper(self) -> None:
        # The wrapper dies on SIGINT but its child ignores it. Killing only the
        # wrapper would leave the child running, so teardown kills the group.
        script = str(SCRIPTS / "iocsh-child-ignores-sigint.py")
        ioc = IOC(executable=script)
        ioc.start()
        wait_for(lambda: "GRANDCHILD_PID=" in ioc.output, timeout=5.0)
        line = next(
            x for x in ioc.output.splitlines() if x.startswith("GRANDCHILD_PID=")
        )
        grandchild = int(line.split("=", 1)[1])
        assert _process_alive(grandchild)

        ioc.kill()

        wait_for(lambda: not _process_alive(grandchild), timeout=5.0)

    def test_teardown_sends_sigint_first(self) -> None:
        # The IOC gets a clean-shutdown signal before any forceful one.
        script = str(SCRIPTS / "iocsh-catches-sigint.py")
        ioc = IOC(executable=script)
        ioc.start()
        ioc.wait_for_output()
        ioc.kill()
        assert "CLEAN_SHUTDOWN_ON_SIGINT" in ioc.output

    def test_teardown_escalates_when_sigint_is_ignored(self) -> None:
        script = str(SCRIPTS / "iocsh-ignores-sigint.py")
        ioc = IOC(executable=script)
        ioc.start()
        ioc.wait_for_output()
        ioc.kill()  # must still return, via SIGKILL
        assert not ioc.is_running()


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
            with IOC(executable=script, exit_timeout=0.3) as ioc:
                ioc.wait_for_output(pattern="WILL_NOT_APPEAR", timeout=0.1)

    def test_detected_error_beats_a_later_exit_timeout(self) -> None:
        # The IOC logged a real error and then ignored exit. The error is the
        # actionable failure; the exit timeout is a downstream symptom.
        script = str(SCRIPTS / "iocsh-error-then-ignores-exit.py")
        with pytest.raises(IocshPatternMatchError, match="ERROR"):
            with IOC(executable=script, exit_timeout=0.3) as ioc:
                ioc.wait_for_output()

    def test_exit_failure_does_not_mask_the_original_error(self) -> None:
        # This IOC ignores the exit command, so exit() times out too. The
        # caller needs to hear that it never became ready, not that it then
        # also refused to leave.
        script = str(SCRIPTS / "iocsh-timeout.py")
        with pytest.raises(IocshTimeoutError, match="WILL_NOT_APPEAR"):
            with IOC(executable=script, exit_timeout=0.3) as ioc:
                ioc.wait_for_output(pattern="WILL_NOT_APPEAR", timeout=0.1)

    def test_none_timeout_returns_when_pattern_found(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script) as ioc:
            ioc.wait_for_output(timeout=None)

    def test_output_accessible_before_exit(self) -> None:
        # Readiness arrives on stderr: EPICS sends errlog there.
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script) as ioc:
            ioc.wait_for_output()
            assert "iocRun: All initialization complete" in ioc.output
            assert "iocRun: All initialization complete" in ioc.stderr

    def test_output_accessible_after_exit(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script, exit_timeout=5.0) as ioc:
            ioc.wait_for_output()
        assert "iocRun: All initialization complete" in ioc.output
        assert 'epicsEnvSet IOCSH_TOP "/tmp"' in ioc.stdout

    def test_stderr_accessible_after_exit(self) -> None:
        script = str(SCRIPTS / "iocsh-module-not-found.py")
        with pytest.raises(IocshModuleNotFoundError):
            with IOC(executable=script, exit_timeout=5.0) as ioc:
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
