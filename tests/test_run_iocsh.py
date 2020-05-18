import logging
import pytest
import re
from click.testing import CliRunner
from run_iocsh import (
    run_iocsh,
    main,
    IocshModuleNotFoundError,
    IocshTimeoutExpired,
    IOC,
)
from epics import PV
from time import sleep


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
        run_iocsh("iocsh.bash", 1)
    assert "require_registerRecordDeviceDriver" in caplog.text
    assert "Loading module info records for require" in caplog.text


def test_run_iocsh_load_module(caplog):
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh.bash", 2, "-r", "iocstats")
    assert "Loaded iocstats version" in caplog.text
    assert "Loading module info records for iocstats" in caplog.text


def test_run_iocsh_module_not_found():
    with pytest.raises(IocshModuleNotFoundError) as excinfo:
        run_iocsh("iocsh.bash", 1, "-r", "foo")
    assert "Module foo not available" == str(excinfo.value)


def test_run_iocsh_module_version_not_found():
    with pytest.raises(IocshModuleNotFoundError) as excinfo:
        run_iocsh("iocsh.bash", 1, "-r", "iocstats,1234")
    assert "Module iocstats version 1234 not available" == str(excinfo.value)


def test_run_iocsh_execute_cmd_file(caplog):
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh.bash", 2, "tests/cmds/test.cmd")
    assert "Loaded iocstats version" in caplog.text
    assert 'runScript("iocStats.iocsh", "IOCNAME=TEST1:")' in caplog.text
    assert 'dbLoadRecords("iocAdminSoft-ess.db", "IOC=TEST1:-IocStats")' in caplog.text


def test_run_iocsh_cmd_file_not_found():
    with pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh.bash", 1, "cmds/foo.cmd")
    assert "No such file or directory: 'cmds/foo.cmd'" == str(excinfo.value)


def test_run_iocsh_autosave(caplog):
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh.bash", 2, "tests/cmds/test_autosave.cmd")
    assert "Loaded autosave version" in caplog.text


def test_run_iocsh_autosave_file_not_found(caplog):
    with caplog.at_level(logging.INFO), pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh.bash", 2, "tests/cmds/test_autosave_file_not_found.cmd")
    autosave_dir = get_module_dir(caplog.text, "autosave")
    assert "No such file or directory: '{}foo.iocsh'".format(autosave_dir) == str(
        excinfo.value
    )


def test_run_iocsh_acf_file_not_found(caplog):
    with caplog.at_level(logging.INFO), pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh.bash", 2, "tests/cmds/test_acf_file_not_found.cmd")
    ess_dir = get_module_dir(caplog.text, "ess")
    assert "No such file or directory: '{}/unknown_access.acf'".format(ess_dir) == str(
        excinfo.value
    )


def test_split_run():
    ioc = IOC()
    assert not ioc.is_running()

    ioc.run("iocsh.bash")
    assert ioc.is_running()

    ioc.exit()
    assert not ioc.is_running()


def test_runiocsh_with_pvaccess():
    ioc = IOC()
    ioc.run("iocsh.bash", "tests/cmds/test_pv.cmd")

    pv = PV("TEST")
    assert int(pv.get()) == 5

    pv.put("17")
    sleep(1)
    assert int(pv.get()) == 17

    ioc.exit()


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
