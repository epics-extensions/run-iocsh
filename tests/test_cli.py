import pytest

from run_iocsh.cli import parse_arguments


# TODO In python 3.6 there is no way to write failing tests for argparse because
# it exits on fail. A solution was introduced in 3.9 with the argument
# exit_on_error. New tests should be added when our requirements change to
# python 3.9.
@pytest.mark.parametrize(
    "args",
    [
        ("--delay", "1", "tests/cmds/test.cmd"),
        ("--name", "iocsh", "tests/cmds/test.cmd"),
        ("--timeout", "1", "tests/cmds/test.cmd"),
        ("-r", "iocstats"),
    ],
)
def test_run_exit_without_error_code(args: tuple[str]) -> int:
    # If parse_args fail the test will exit with return value != 0
    parse_arguments(args)
