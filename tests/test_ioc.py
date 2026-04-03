import logging
from pathlib import Path

import pytest

from run_iocsh import (
    IOC,
    IocshAlreadyRunningError,
    IocshFileNotFoundError,
    IocshMissingSharedLibraryError,
    IocshModuleNotFoundError,
    IocshPatternMatchError,
    IocshStartupError,
    IocshStateError,
    IocshTimeoutError,
    run_iocsh,
    wait_for,
)
from run_iocsh.ioc import RE_BUILTIN_FAIL_ON

SCRIPTS = Path(__file__).parent / "scripts"


def test_run_iocsh_output_in_pylog(caplog: pytest.LogCaptureFixture) -> None:
    script = str(SCRIPTS / "iocsh-print-and-exit.py")
    with caplog.at_level(logging.DEBUG, logger="run_iocsh"):
        run_iocsh(executable=script, delay=0)
    assert "iocRun: All initialization complete" in caplog.text


def test_split_run() -> None:
    script = str(SCRIPTS / "iocsh-wait-for-exit.py")
    ioc = IOC(executable=script, timeout=5.0)
    assert not ioc.is_running()
    assert ioc.pid is None

    ioc.start()
    assert ioc.is_running()
    assert ioc.pid is not None

    ioc.exit()
    assert not ioc.is_running()


def test_already_running() -> None:
    script = str(SCRIPTS / "iocsh-print-and-exit.py")
    with (
        pytest.raises(IocshAlreadyRunningError) as excinfo,
        IOC(executable=script, timeout=5.0) as ioc,
    ):
        ioc.start()

    assert "IOC already running" in str(excinfo.value)


def test_doubleexit(caplog: pytest.LogCaptureFixture) -> None:
    script = str(SCRIPTS / "iocsh-print-and-exit.py")
    with caplog.at_level(logging.WARNING):
        with IOC(executable=script, timeout=5.0) as ioc:
            pass
        ioc.exit()
    assert "IOC is not running" in caplog.text


def test_check_output_before_exit_raises() -> None:
    script = str(SCRIPTS / "iocsh-custom-error.py")
    with pytest.raises(IocshStateError):
        IOC(executable=script).check_output()


class TestWaitFor:
    def test_returns_when_predicate_true(self) -> None:
        wait_for(lambda: True, timeout=1.0)

    def test_raises_on_timeout(self) -> None:
        with pytest.raises(TimeoutError):
            wait_for(lambda: False, timeout=0.05, poll_interval=0.01)

    def test_swallows_predicate_exceptions(self) -> None:
        call_count = 0

        def flaky() -> bool:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = "not ready yet"
                raise RuntimeError(msg)
            return True

        wait_for(flaky, timeout=1.0, poll_interval=0.01)
        assert call_count >= 3

    def test_timeout_message_contains_duration(self) -> None:
        with pytest.raises(TimeoutError, match=r"0\.05s"):
            wait_for(lambda: False, timeout=0.05, poll_interval=0.01)


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
        assert "Module mock version fake not available" in ioc.stderr

    def test_caplog_captures_output_at_debug(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with caplog.at_level(logging.DEBUG, logger="run_iocsh"):
            with IOC(executable=script) as ioc:
                ioc.wait_for_output()
        assert "iocRun: All initialization complete" in caplog.text


class TestExceptions:
    def test_run_iocsh_script_not_found(self) -> None:
        with pytest.raises(FileNotFoundError) as excinfo:
            run_iocsh(executable="foo")
        assert "No such file or directory: 'foo'" in str(excinfo.value)

    def test_run_iocsh_cmd_file_not_found(self) -> None:
        filename = "does-not-exist.cmd"
        script = str(SCRIPTS / "iocsh-cant-open.py")
        with pytest.raises(IocshFileNotFoundError) as excinfo:
            run_iocsh(filename, executable=script, delay=0.1)
        assert f"No such file or directory: '{filename}'" in str(excinfo.value)

    def test_run_iocsh_module_version_not_found(self) -> None:
        module_name = "mock"
        module_version = "fake"
        script = str(SCRIPTS / "iocsh-module-not-found.py")
        with pytest.raises(IocshModuleNotFoundError) as excinfo:
            run_iocsh(
                "-r",
                f"{module_name},{module_version}",
                delay=0.1,
                executable=script,
            )
        assert (
            str(excinfo.value)
            == f"Module {module_name} version {module_version} not available"
        )

    def test_run_iocsh_module_not_found(self) -> None:
        script = str(SCRIPTS / "iocsh-module-not-found.py")
        with pytest.raises(IocshModuleNotFoundError) as excinfo:
            run_iocsh("-r", "foo", executable=script, delay=0)
        assert str(excinfo.value) == "Module foo not available"

    def test_run_iocsh_iocshload_file_not_found(self) -> None:
        nonexistent_file = "fake"
        script = str(SCRIPTS / "iocsh-file-not-exist.py")
        with pytest.raises(IocshFileNotFoundError) as excinfo:
            run_iocsh(executable=script, delay=0.1)
        assert f"No such file or directory: '{nonexistent_file}'" in str(excinfo.value)

    def test_missing_shared_lib(self) -> None:
        script = str(SCRIPTS / "iocsh-missing-shared-lib.py")
        with pytest.raises(IocshMissingSharedLibraryError) as excinfo:
            run_iocsh(executable=script, delay=0)
        assert str(excinfo.value) == "Missing shared library: 'liblib'"

    @pytest.mark.parametrize("name", ["iocsh-timeout.py", "iocsh-stdout-closed.py"])
    def test_run_iocsh_timeout_expired(self, name: str) -> None:
        with pytest.raises(IocshTimeoutError) as excinfo:
            run_iocsh(delay=0.1, timeout=0.5, executable=str(SCRIPTS / name))
        assert str(excinfo.value) == "Failed to send exit to the IOC"


class TestCheckOutputFailOn:
    def test_builtin_error_pattern_detected(self) -> None:
        script = str(SCRIPTS / "iocsh-error-output.py")
        with pytest.raises(IocshPatternMatchError, match="ERROR"):
            run_iocsh(delay=0.1, executable=script)

    def test_user_fail_on_pattern_raises(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        with pytest.raises(IocshPatternMatchError, match="CUSTOM_ERROR:"):
            run_iocsh(delay=0.1, executable=script, fail_on=["CUSTOM_ERROR:"])

    def test_user_fail_on_no_match_does_not_raise(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        run_iocsh(delay=0.1, executable=script, fail_on=["WILL_NOT_MATCH"])

    def test_builtin_fail_on_is_exported(self) -> None:
        assert isinstance(RE_BUILTIN_FAIL_ON, tuple)
        assert any("ERROR" in p for p in RE_BUILTIN_FAIL_ON)

    def test_fail_on_is_additive_to_builtins(self) -> None:
        # Builtins still fire even when a custom fail_on is also passed
        script = str(SCRIPTS / "iocsh-error-output.py")
        with pytest.raises(IocshPatternMatchError, match="ERROR"):
            run_iocsh(delay=0.1, executable=script, fail_on=["WILL_NOT_MATCH"])
