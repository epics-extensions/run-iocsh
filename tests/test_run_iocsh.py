import logging
import re
from time import sleep
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


def get_module_dir(logtext: str, module: str) -> str:
    match = re.search(f"Module {module} version " + r".* found in (.*)\n", logtext)
    return match.group(1) if match else ""


def test_run_iocsh_script_not_found() -> None:
    with pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("foo", 1)
    assert "No such file or directory: 'foo'" in str(excinfo.value)


def test_run_iocsh_no_args(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 1)
    assert "require_registerRecordDeviceDriver" in caplog.text
    assert "Loading module info records for require" in caplog.text


def test_run_iocsh_load_module(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, "-r", "iocstats")
    assert "Loaded iocstats version" in caplog.text
    assert "Loading module info records for iocstats" in caplog.text


def test_run_iocsh_module_not_found() -> None:
    with pytest.raises(IocshModuleNotFoundError) as excinfo:
        run_iocsh("iocsh", 1, "-r", "foo")
    assert str(excinfo.value) == "Module foo not available"


def test_run_iocsh_module_version_not_found() -> None:
    with pytest.raises(IocshModuleNotFoundError) as excinfo:
        run_iocsh("iocsh", 1, "-r", "iocstats,1234")
    assert str(excinfo.value) == "Module iocstats version 1234 not available"


def test_run_iocsh_execute_cmd_file(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, "tests/cmds/test.cmd")
    assert "Loaded iocstats version" in caplog.text
    assert 'runScript("iocStats.iocsh", "IOCNAME=TEST1:")' in caplog.text
    assert 'dbLoadRecords("iocAdminSoft-ess.db", "IOC=TEST1:")' in caplog.text


def test_run_iocsh_cmd_file_not_found() -> None:
    with pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh", 1, "cmds/foo.cmd")
    assert str(excinfo.value) == "No such file or directory: 'cmds/foo.cmd'"


def test_run_iocsh_autosave(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, "tests/cmds/test_autosave.cmd")
    assert "Loaded autosave version" in caplog.text


def test_run_iocsh_autosave_file_not_found(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO), pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh", 2, "tests/cmds/test_autosave_file_not_found.cmd")
    autosave_dir = get_module_dir(caplog.text, "autosave")
    assert f"No such file or directory: '{autosave_dir}foo.iocsh'" == str(excinfo.value)


def test_run_iocsh_acf_file_not_found(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO), pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh", 2, "tests/cmds/test_acf_file_not_found.cmd")
    essioc_dir = get_module_dir(caplog.text, "essioc")
    assert f"No such file or directory: '{essioc_dir}/unknown_access.acf'" == str(
        excinfo.value
    )


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


def test_missing_shared_lib() -> None:
    with pytest.raises(MissingSharedLibraryError) as excinfo:
        run_iocsh("iocsh", 1, "tests/cmds/test_missing_shared_lib.cmd")
    assert str(excinfo.value) == "Missing shared library: 'liblib'"


def test_runiocsh_ca() -> None:
    from epics import PV

    with IOC("tests/cmds/test_pv.cmd"):
        pv = PV("TEST")
        value_in_db = 5
        assert int(pv.get()) == value_in_db

        new_value = 17
        pv.put(str(new_value))
        sleep(0.1)
        assert int(pv.get()) == new_value


def test_pvapy() -> None:
    from pvaccess import Channel, PvDouble

    with IOC("tests/cmds/test_pv.cmd"):
        channel = Channel("TEST")
        value = 13.0
        channel.put(PvDouble(value))
        sleep(0.1)
        assert channel.get().get()["value"] == value


def test_p4p() -> None:
    from p4p.client.thread import Context

    assert "pva" in Context.providers()

    with IOC("tests/cmds/test_pv.cmd"), Context("pva") as ctxt:
        value = 19
        ctxt.put("TEST", value)
        assert ctxt.get("TEST") == value


def test_doubleexit(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        with IOC() as ioc:
            pass
        ioc.exit()
    assert "IOC is not running" in caplog.text


@pytest.mark.parametrize("name", ["iocsh-timeout.bash", "iocsh-stdin-closed.bash"])
def test_run_iocsh_timeout_expired(name: str) -> None:
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
