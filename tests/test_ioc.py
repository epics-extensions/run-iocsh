import logging
from pathlib import Path
from typing import Tuple
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
)


def mocked_iocsh_subprocess_communicate_retval(
    module_name: str, module_version: str
) -> Tuple[bytes, bytes]:
    outs = b""
    errs = f"Module {module_name} version {module_version} not available".encode()
    return outs, errs


def test_split_run() -> None:
    ioc = IOC()
    assert not ioc.is_running()

    ioc.start()
    assert ioc.is_running()

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


class TestExceptions:
    def test_run_iocsh_script_not_found(self) -> None:
        with pytest.raises(FileNotFoundError) as excinfo:
            run_iocsh("foo", 1)
        assert "No such file or directory: 'foo'" in str(excinfo.value)

    def test_run_iocsh_cmd_file_not_found(self) -> None:
        filename = "does-not-exist.cmd"
        # Different versions of require will generate different errors in this
        # case, which in turn will take different paths in run-iocsh.
        # Because of this we accept both exception types and check the message.
        with pytest.raises((FileNotFoundError, IocshProcessError)) as excinfo:
            run_iocsh("iocsh", 1, filename)
        assert f"No such file or directory: '{filename}'" in str(excinfo.value)

    @patch("subprocess.Popen")
    def test_run_iocsh_module_version_not_found(self, popen_mock: Mock) -> None:
        module_name = "mock"
        module_version = "fake"

        process_mock = popen_mock.Mock()
        process_mock.communicate.return_value = (
            mocked_iocsh_subprocess_communicate_retval(module_name, module_version)
        )
        process_mock.returncode = 0
        popen_mock.return_value = process_mock

        with pytest.raises(IocshModuleNotFoundError) as excinfo:
            run_iocsh("iocsh", 1, "-r", f"{module_name},{module_version}")
        assert (
            str(excinfo.value)
            == f"Module {module_name} version {module_version} not available"
        )

    def test_run_iocsh_module_not_found(self) -> None:
        with pytest.raises(IocshModuleNotFoundError) as excinfo:
            run_iocsh("iocsh", 1, "-r", "foo")
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
            run_iocsh("iocsh", 2, tmp_file.as_posix())
        assert f"No such file or directory: '{nonexistent_file}'" == str(excinfo.value)

    def test_missing_shared_lib(self, tmp_path: Path) -> None:
        file_contents = """\
echo "liblib: cannot open shared object file"
"""
        tmp_file = tmp_path / "test_missing_shared_lib.cmd"
        tmp_file.write_text(file_contents)

        with pytest.raises(MissingSharedLibraryError) as excinfo:
            run_iocsh("iocsh", 1, tmp_file.as_posix())
        assert str(excinfo.value) == "Missing shared library: 'liblib'"

    @pytest.mark.parametrize("name", ["iocsh-timeout.bash", "iocsh-stdin-closed.bash"])
    def test_run_iocsh_timeout_expired(self, name: str) -> None:
        with pytest.raises(IocshTimeoutExpiredError) as excinfo:
            run_iocsh(f"./tests/scripts/{name}", 0.1, timeout=0.5)
        assert str(excinfo.value) == "Failed to send exit to the IOC"
