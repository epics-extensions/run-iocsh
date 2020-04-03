import logging
import pytest
from click.testing import CliRunner
from run_iocsh import run_iocsh, main, IocshModuleNotFoundError, IocshTimeoutExpired


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


def test_run_iocsh_acf_file_not_found():
    with pytest.raises(FileNotFoundError) as excinfo:
        run_iocsh("iocsh.bash", 2, "tests/cmds/test_acf_file_not_found.cmd")
    assert (
        "No such file or directory: '/opt/conda/envs/test/modules/ess/0.3.0//unknown_access.acf'"
        == str(excinfo.value)
    )


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
