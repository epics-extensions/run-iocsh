import logging
from pathlib import Path
from typing import Tuple

import pytest

from run_iocsh import (
    IOC,
    IocshAlreadyRunningError,
    IocshModuleNotFoundError,
    IocshTimeoutExpiredError,
    MissingSharedLibraryError,
    parse_arguments,
    run_iocsh,
)

from .utils import get_module_dir


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
        with pytest.raises(FileNotFoundError) as excinfo:
            run_iocsh("iocsh", 1, filename)
        assert str(excinfo.value) == f"No such file or directory: '{filename}'"

    def test_run_iocsh_module_version_not_found(self) -> None:
        with pytest.raises(IocshModuleNotFoundError) as excinfo:
            run_iocsh("iocsh", 1, "-r", "iocstats,1234")
        assert str(excinfo.value) == "Module iocstats version 1234 not available"

    def test_run_iocsh_module_not_found(self) -> None:
        with pytest.raises(IocshModuleNotFoundError) as excinfo:
            run_iocsh("iocsh", 1, "-r", "foo")
        assert str(excinfo.value) == "Module foo not available"

    def test_run_iocsh_autosave_file_not_found(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        file_contents = """\
require autosave

epicsEnvSet("IOCNAME", "myioc")
epicsEnvSet("AS_TOP", "/tmp")

iocshLoad("$(autosave_DIR)/autosave.iocsh", "AS_TOP=$(AS_TOP), IOCNAME=$(IOCNAME)")
iocshLoad("$(autosave_DIR)foo.iocsh", "AS_TOP=$(AS_TOP), IOCNAME=$(IOCNAME)")
"""
        tmp_file = tmp_path / "test_autosave_file_not_found.cmd"
        tmp_file.write_text(file_contents)

        with caplog.at_level(logging.INFO), pytest.raises(FileNotFoundError) as excinfo:
            run_iocsh("iocsh", 2, tmp_file.as_posix())
        autosave_dir = get_module_dir(caplog.text, "autosave")
        assert f"No such file or directory: '{autosave_dir}foo.iocsh'" == str(
            excinfo.value
        )

    def test_run_iocsh_acf_file_not_found(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        file_contents = """\
require essioc

epicsEnvSet("PATH_TO_ASG_FILES", "$(essioc_DIR)")
# Use non existing file
epicsEnvSet("ASG_FILENAME", "$(ASG_FILENAME=unknown_access.acf)")

iocshLoad("$(essioc_DIR)/accessSecurityGroup.iocsh", "ASG_PATH=$(PATH_TO_ASG_FILES),ASG_FILE=$(ASG_FILENAME)")
"""  # noqa: E501
        tmp_file = tmp_path / "test_acf_file_not_found.cmd"
        tmp_file.write_text(file_contents)

        with caplog.at_level(logging.INFO), pytest.raises(FileNotFoundError) as excinfo:
            run_iocsh("iocsh", 2, tmp_file.as_posix())
        essioc_dir = get_module_dir(caplog.text, "essioc")
        assert f"No such file or directory: '{essioc_dir}/unknown_access.acf'" == str(
            excinfo.value
        )

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


# TODO In python 3.6 there is no way to write failing tests for argparse because
# it exits on fail. A solution was introduced in 3.9 with the argument
# exit_on_error. New tests should be added when our requirements change to
# python 3.9.
@pytest.mark.parametrize(
    "args",
    [
        ("--delay", "1", "-r", "iocstats"),
        ("--delay", "1", "tests/cmds/test.cmd"),
        ("--name", "iocsh", "tests/cmds/test.cmd"),
        ("--timeout", "1", "tests/cmds/test.cmd"),
        ("--name", "iocsh.bash", "--delay", "1", "-timeout", "1", "-r", "iocstats"),
        ("-r", "iocstats"),
    ],
)
def test_run_exit_without_error_code(args: Tuple[str]) -> int:
    # If parse_args fail the test will exit with return value != 0
    parse_arguments(args)
