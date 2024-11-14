import logging
from pathlib import Path
from typing import Tuple
from unittest.mock import patch

import pytest

from run_iocsh import run_iocsh


def mocked_iocsh_subprocess_communicate_retval(module_name: str) -> Tuple[bytes, bytes]:
    outs = f"""\
Loaded {module_name} version not-a-real-version
Loading module info records for {module_name}
""".encode()
    errs = b""
    return outs, errs


def test_run_iocsh_no_args(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        run_iocsh("iocsh", 1)
    assert "require_registerRecordDeviceDriver" in caplog.text
    assert "Loading module info records for require" in caplog.text


def test_run_iocsh_load_module(caplog: pytest.LogCaptureFixture) -> None:
    module_name = "mock"
    with caplog.at_level(logging.INFO), patch("subprocess.Popen") as popen_mock:
        process_mock = popen_mock.Mock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (
            mocked_iocsh_subprocess_communicate_retval(module_name)
        )
        popen_mock.return_value = process_mock

        run_iocsh("iocsh", 2, "-r", module_name)
    assert f"Loaded {module_name} version" in caplog.text
    assert f"Loading module info records for {module_name}" in caplog.text


def test_run_iocsh_module_loading(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    module_name = "mock"
    file_contents = f"""\
require {module_name}
"""
    tmp_file = tmp_path / "test_module_loading.cmd"
    tmp_file.write_text(file_contents)

    with caplog.at_level(logging.INFO), patch("subprocess.Popen") as popen_mock:
        process_mock = popen_mock.Mock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (
            mocked_iocsh_subprocess_communicate_retval(module_name)
        )
        popen_mock.return_value = process_mock

        run_iocsh("iocsh", 2, tmp_file.as_posix())
    assert f"Loaded {module_name} version" in caplog.text
