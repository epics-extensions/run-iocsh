import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from run_iocsh.cli import main, parse_arguments

SCRIPTS = Path(__file__).parent / "scripts"


@pytest.mark.parametrize(
    "args",
    [
        ("--delay", "1", "nonexistent.cmd"),
        ("--timeout", "1", "nonexistent.cmd"),
        ("--executable", "iocsh", "nonexistent.cmd"),
        ("-r", "iocstats"),
        ("--unknown-flag", "value", "nonexistent.cmd"),
    ],
)
def test_parse_arguments_does_not_raise(args: tuple[str]) -> None:
    parse_arguments(args)


class TestMain:
    def test_success_exits_zero(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with patch.object(sys, "argv", ["run-iocsh", "--executable", script]):
            main()

    def test_missing_executable_exits_one(self) -> None:
        with patch.object(sys, "argv", ["run-iocsh", "--executable", "does-not-exist"]):
            with pytest.raises(SystemExit) as excinfo:
                main()
        assert excinfo.value.code == 1

    def test_fail_on_pattern_exits_one(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        with patch.object(
            sys,
            "argv",
            ["run-iocsh", "--executable", script, "--fail-on", "CUSTOM_ERROR:"],
        ):
            with pytest.raises(SystemExit) as excinfo:
                main()
        assert excinfo.value.code == 1

    def test_fail_on_no_match_exits_zero(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        with patch.object(
            sys,
            "argv",
            ["run-iocsh", "--executable", script, "--fail-on", "WILL_NOT_MATCH"],
        ):
            main()
