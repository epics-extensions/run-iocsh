import logging
from pathlib import Path

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


def test_run_iocsh_module_loading(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    file_contents = """\
require iocstats
"""
    tmp_file = tmp_path / "test_module_loading.cmd"
    tmp_file.write_text(file_contents)

    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, tmp_file.as_posix())
    assert "Loaded iocstats version" in caplog.text


def test_run_iocsh_autosave(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    file_contents = """\
require autosave

epicsEnvSet("IOCNAME", "myioc")
epicsEnvSet("AS_TOP", "/tmp")

iocshLoad("$(autosave_DIR)/autosave.iocsh", "AS_TOP=$(AS_TOP), IOCNAME=$(IOCNAME)")
"""
    tmp_file = tmp_path / "test_autosave.cmd"
    tmp_file.write_text(file_contents)

    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 2, tmp_file.as_posix())
    assert "Loaded autosave version" in caplog.text
