import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from run_iocsh import (
    IOC,
    IocshAlreadyRunningError,
    IocshModuleNotFoundError,
    IocshProcessError,
    IocshTimeoutExpiredError,
    MissingSharedLibraryError,
    run_iocsh,
    wait_for,
)


def mocked_iocsh_module_unavailable_subprocess_communicate_retval(
    module_name: str, module_version: str
) -> tuple[bytes, bytes]:
    outs = b""
    errs = f"Module {module_name} version {module_version} not available".encode()
    return outs, errs


def test_run_iocsh_output_in_pylog(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        run_iocsh(delay=1)
    assert "require_registerRecordDeviceDriver" in caplog.text
    assert "Loading module info records for require" in caplog.text


def test_split_run() -> None:
    ioc = IOC()
    assert not ioc.is_running()
    assert ioc.pid is None

    ioc.start()
    assert ioc.is_running()
    assert ioc.pid is not None

    ioc.exit()
    assert not ioc.is_running()


def test_already_running() -> None:
    with pytest.raises(IocshAlreadyRunningError) as excinfo, IOC() as ioc:
        ioc.start()

    assert "IOC already running" in str(excinfo.value)


def test_doubleexit(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        with IOC() as ioc:
            pass
        ioc.exit()
    assert "IOC is not running" in caplog.text


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


class TestExceptions:
    def test_run_iocsh_script_not_found(self) -> None:
        with pytest.raises(FileNotFoundError) as excinfo:
            run_iocsh(executable="foo")
        assert "No such file or directory: 'foo'" in str(excinfo.value)

    def test_run_iocsh_cmd_file_not_found(self) -> None:
        filename = "does-not-exist.cmd"
        # Different versions of require will generate different errors in this
        # case, which in turn will take different paths in run-iocsh.
        # Because of this we accept both exception types and check the message.
        with pytest.raises((FileNotFoundError, IocshProcessError)) as excinfo:
            run_iocsh(filename, delay=1)
        assert f"No such file or directory: '{filename}'" in str(excinfo.value)

    @patch("subprocess.Popen")
    def test_run_iocsh_module_version_not_found(self, popen_mock: Mock) -> None:
        module_name = "mock"
        module_version = "fake"

        process_mock = popen_mock.Mock()
        process_mock.communicate.return_value = (
            mocked_iocsh_module_unavailable_subprocess_communicate_retval(
                module_name, module_version
            )
        )
        process_mock.returncode = 0
        popen_mock.return_value = process_mock

        with pytest.raises(IocshModuleNotFoundError) as excinfo:
            run_iocsh("-r", f"{module_name},{module_version}", delay=1)
        assert (
            str(excinfo.value)
            == f"Module {module_name} version {module_version} not available"
        )

    def test_run_iocsh_module_not_found(self) -> None:
        with pytest.raises(IocshModuleNotFoundError) as excinfo:
            run_iocsh("-r", "foo", delay=1)
        assert str(excinfo.value) == "Module foo not available"

    def test_run_iocsh_iocshload_file_not_found(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        nonexistent_file = "fake"
        file_contents = f"""\
iocshLoad("{nonexistent_file}")
"""
        tmp_file = tmp_path / "test_iocshload_file_not_found.cmd"
        tmp_file.write_text(file_contents)

        with caplog.at_level(logging.INFO), pytest.raises(FileNotFoundError) as excinfo:
            run_iocsh(tmp_file.as_posix(), delay=2)
        assert f"No such file or directory: '{nonexistent_file}'" == str(excinfo.value)

    def test_missing_shared_lib(self, tmp_path: Path) -> None:
        file_contents = """\
echo "liblib: cannot open shared object file"
"""
        tmp_file = tmp_path / "test_missing_shared_lib.cmd"
        tmp_file.write_text(file_contents)

        with pytest.raises(MissingSharedLibraryError) as excinfo:
            run_iocsh(tmp_file.as_posix(), delay=1)
        assert str(excinfo.value) == "Missing shared library: 'liblib'"

    @pytest.mark.parametrize("name", ["iocsh-timeout.bash", "iocsh-stdin-closed.bash"])
    def test_run_iocsh_timeout_expired(self, name: str) -> None:
        test_data_dir = Path(__file__).parent / "scripts"
        with pytest.raises(IocshTimeoutExpiredError) as excinfo:
            run_iocsh(delay=0.1, timeout=0.5, executable=str(test_data_dir / name))
        assert str(excinfo.value) == "Failed to send exit to the IOC"
