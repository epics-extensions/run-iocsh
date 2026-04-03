import pytest

from run_iocsh.cli import parse_arguments


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
