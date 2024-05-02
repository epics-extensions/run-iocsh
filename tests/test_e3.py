import logging

import pytest

from run_iocsh import run_iocsh


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


def test_run_iocsh_module_loading(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, "tests/cmds/test_module_loading.cmd")
    assert "Loaded iocstats version" in caplog.text


def test_run_iocsh_autosave(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, "tests/cmds/test_autosave.cmd")
    assert "Loaded autosave version" in caplog.text
