import logging
import re
from time import sleep

import pytest
from click.testing import CliRunner

from run_iocsh import (
    IOC,
    IocshAlreadyRunning,
    IocshModuleNotFoundError,
    IocshTimeoutExpired,
    MissingSharedLibrary,
    main,
    run_iocsh,
)


def get_module_dir(logtext: str, module: str):
    match = re.search(
        "Module {} version ".format(module) + r".* found in (.*)\n", logtext
    )
    return match.group(1) if match else ""


def test_run_iocsh_script_not_found():
    with pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("foo", 1)
    assert "No such file or directory: 'foo'" in str(excinfo.value)


def test_run_iocsh_no_args(caplog):
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 1)
    assert "require_registerRecordDeviceDriver" in caplog.text
    assert "Loading module info records for require" in caplog.text


def test_run_iocsh_load_module(caplog):
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, "-r", "iocstats")
    assert "Loaded iocstats version" in caplog.text
    assert "Loading module info records for iocstats" in caplog.text


def test_run_iocsh_module_not_found():
    with pytest.raises(IocshModuleNotFoundError) as excinfo:
        run_iocsh("iocsh", 1, "-r", "foo")
    assert "Module foo not available" == str(excinfo.value)


def test_run_iocsh_module_version_not_found():
    with pytest.raises(IocshModuleNotFoundError) as excinfo:
        run_iocsh("iocsh", 1, "-r", "iocstats,1234")
    assert "Module iocstats version 1234 not available" == str(excinfo.value)


def test_run_iocsh_execute_cmd_file(caplog):
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, "tests/cmds/test.cmd")
    assert "Loaded iocstats version" in caplog.text
    assert 'runScript("iocStats.iocsh", "IOCNAME=TEST1:")' in caplog.text
    assert 'dbLoadRecords("iocAdminSoft-ess.db", "IOC=TEST1:")' in caplog.text


def test_run_iocsh_cmd_file_not_found():
    with pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh", 1, "cmds/foo.cmd")
    assert "No such file or directory: 'cmds/foo.cmd'" == str(excinfo.value)


def test_run_iocsh_autosave(caplog):
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, "tests/cmds/test_autosave.cmd")
    assert "Loaded autosave version" in caplog.text


def test_run_iocsh_autosave_file_not_found(caplog):
    with caplog.at_level(logging.INFO), pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh", 2, "tests/cmds/test_autosave_file_not_found.cmd")
    autosave_dir = get_module_dir(caplog.text, "autosave")
    assert f"No such file or directory: '{autosave_dir}foo.iocsh'" == str(excinfo.value)


def test_run_iocsh_acf_file_not_found(caplog):
    with caplog.at_level(logging.INFO), pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh", 2, "tests/cmds/test_acf_file_not_found.cmd")
    auth_dir = get_module_dir(caplog.text, "auth")
    assert f"No such file or directory: '{auth_dir}/unknown_access.acf'" == str(
        excinfo.value
    )


def test_split_run():
    ioc = IOC()
    assert not ioc.is_running()

    ioc.start()
    assert ioc.is_running()

    ioc.exit()
    assert not ioc.is_running()


def test_already_running():
    with pytest.raises(IocshAlreadyRunning) as excinfo, IOC() as ioc:
        ioc.start()

    assert "IOC already running" in str(excinfo.value)


def test_missing_shared_lib():
    with pytest.raises(MissingSharedLibrary) as excinfo:
        run_iocsh("iocsh", 1, "tests/cmds/test_missing_shared_lib.cmd")
    assert "Missing shared library: 'liblib'" == str(excinfo.value)


def test_runiocsh_ca():
    from epics import PV

    with IOC("tests/cmds/test_pv.cmd"):
        pv = PV("TEST")
        assert int(pv.get()) == 5

        pv.put("17")
        sleep(0.1)
        assert int(pv.get()) == 17


def test_pvapy():
    from pvaccess import Channel, PvDouble

    with IOC("tests/cmds/test_pv.cmd"):
        channel = Channel("TEST")
        channel.put(PvDouble(13.0))
        sleep(0.1)
        assert channel.get().get()["value"] == 13.0


def test_p4p():
    from p4p.client.thread import Context

    assert "pva" in Context.providers()

    with IOC("tests/cmds/test_pv.cmd"), Context("pva") as ctxt:
        ctxt.put("TEST", 19)
        assert ctxt.get("TEST") == 19.0


def test_doubleexit(caplog):
    with caplog.at_level(logging.WARNING):
        with IOC() as ioc:
            pass
        ioc.exit()
    assert "IOC is not running" in caplog.text


@pytest.mark.parametrize("name", ("iocsh-timeout.bash", "iocsh-stdin-closed.bash"))
def test_run_iocsh_timeout_expired(name):
    with pytest.raises(IocshTimeoutExpired) as excinfo:
        run_iocsh(f"./tests/scripts/{name}", 0.1, timeout=0.5)
    assert "Failed to send exit to the IOC" == str(excinfo.value)


@pytest.mark.parametrize(
    "args",
    [
        ("--name", "foo"),
        (
            "--name",
            "./tests/scripts/iocsh-timeout.bash",
            "--delay",
            "0.1",
            "--timeout",
            "0.5",
        ),
        ("--delay", "1", "-r", "foo"),
        ("--delay", "1", "foo.cmd"),
        ("--delay", "1", "-r", "iocstats,1234"),
    ],
)
def test_run_exit_with_error_code(args):
    runner = CliRunner()
    result = runner.invoke(main, args)
    assert result.exit_code == 1


@pytest.mark.parametrize(
    "args",
    [("--delay", "1", "-r", "iocstats"), ("--delay", "1", "tests/cmds/test.cmd")],
)
def test_run_exit_without_error_code(args):
    runner = CliRunner()
    result = runner.invoke(main, args)
    assert result.exit_code == 0
