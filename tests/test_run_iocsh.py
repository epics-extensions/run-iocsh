import logging
import pytest
from run_iocsh import run_iocsh, IocshModuleNotFoundError


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
    with pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh.bash", 2, "tests/cmds/test_autosave_file_not_found.cmd")
    assert (
        "No such file or directory: '/opt/conda/envs/test/modules/autosave/5.10.0/foo.iocsh'"
        == str(excinfo.value)
    )
