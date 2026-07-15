"""CLI entry point for package."""

import argparse
import logging
import sys

from run_iocsh.exceptions import RunIocshError
from run_iocsh.ioc import (
    DEFAULT_EXECUTABLE,
    DEFAULT_EXIT_TIMEOUT,
    DEFAULT_FAIL_ON,
    DEFAULT_INIT_PATTERN,
    DEFAULT_INIT_TIMEOUT,
    run_iocsh,
)

log = logging.getLogger(__name__)

# The CLI checks the IOC stays up: unlike the library it defaults to keeping the
# IOC running for a few seconds, long enough to catch an IOC that starts cleanly
# and then crashes.
DEFAULT_CLI_SETTLE = 5.0

# Flags renamed in 3.0.0. Without these, argparse would hand them to
# parse_known_args' extras and they would be forwarded to the IOC -- turning a
# stale flag into an argument the IOC does not understand, silently.
_RENAMED_FLAGS = {"--delay": "--settle", "--timeout": "--exit-timeout"}


class _RenamedFlag(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):  # noqa: ANN001, ANN204, ARG002
        parser.error(f"{option_string} was renamed to {_RENAMED_FLAGS[option_string]}")


def parse_arguments(  # noqa: D103
    args: list[str] | None = None,
) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Run iocsh and send the exit command after <settle> seconds",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--settle",
        default=DEFAULT_CLI_SETTLE,
        type=float,
        help="time (in seconds) to keep the IOC running after it is ready",
    )

    parser.add_argument(
        "--exit-timeout",
        default=DEFAULT_EXIT_TIMEOUT,
        type=float,
        help="time (in seconds) to wait for the IOC to exit after sending exit",
    )

    parser.add_argument(
        "--init-timeout",
        default=DEFAULT_INIT_TIMEOUT,
        type=float,
        help="time (in seconds) to wait for the IOC to become ready",
    )

    readiness = parser.add_mutually_exclusive_group()
    readiness.add_argument(
        "--pattern",
        default=DEFAULT_INIT_PATTERN,
        help="regex to wait for before considering the IOC ready",
    )
    readiness.add_argument(
        "--no-wait-for-init",
        action="store_true",
        default=False,
        help="do not wait for the IOC to become ready (e.g. with iocsh --no-init)",
    )

    parser.add_argument(
        "--executable",
        default=DEFAULT_EXECUTABLE,
        help="IOC executable to run",
    )

    parser.add_argument(
        "--fail-on",
        action="append",
        dest="fail_on",
        default=[],
        metavar="PATTERN",
        help=(
            "raise if regex PATTERN matches output; ^ERROR is always checked"
            " (may be given multiple times)"
        ),
    )

    parser.add_argument(
        "--no-default-fail-on",
        action="store_true",
        default=False,
        dest="no_default_fail_on",
        help="disable the always-active ^ERROR check",
    )

    for old in _RENAMED_FLAGS:
        parser.add_argument(old, action=_RenamedFlag, nargs="?", help=argparse.SUPPRESS)

    return parser.parse_known_args(args)


def main() -> None:  # noqa: D103
    namespace, extra = parse_arguments()
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s ", level=logging.DEBUG
    )
    try:
        base = () if namespace.no_default_fail_on else DEFAULT_FAIL_ON
        run_iocsh(
            *extra,
            settle=namespace.settle,
            exit_timeout=namespace.exit_timeout,
            init_timeout=namespace.init_timeout,
            pattern=namespace.pattern,
            wait_for_init=not namespace.no_wait_for_init,
            executable=namespace.executable,
            fail_on=base + tuple(namespace.fail_on),
        )
    except (RunIocshError, FileNotFoundError):
        log.exception("Found an error")
        sys.exit(1)
