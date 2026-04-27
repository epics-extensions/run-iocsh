import logging
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
)

SCRIPTS = Path(__file__).parent / "scripts"


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

    def test_returned_ioc_stdout_accessible(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        result = run_iocsh(executable=script, delay=0)
        assert "iocRun: All initialization complete" in result.stdout

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

    def test_stdout_accessible_before_exit(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script) as ioc:
            ioc.wait_for_output()
            assert "iocRun: All initialization complete" in ioc.stdout

    def test_stdout_accessible_after_exit(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with IOC(executable=script, timeout=5.0) as ioc:
            ioc.wait_for_output()
        assert "iocRun: All initialization complete" in ioc.stdout

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
