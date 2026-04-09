"""CLI entry point for package."""

import argparse
import logging
import sys

from run_iocsh.exceptions import RunIocshError
from run_iocsh.ioc import (
    DEFAULT_DELAY,
    DEFAULT_EXECUTABLE,
    DEFAULT_EXIT_TIMEOUT,
    run_iocsh,
)

log = logging.getLogger(__name__)


def parse_arguments(  # noqa: D103
    args: list[str] | None = None,
) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Run iocsh and send the exit command after <delay> seconds",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--delay",
        default=DEFAULT_DELAY,
        type=float,
        help="time (in seconds) to wait after iocInit before sending exit",
    )

    parser.add_argument(
        "--timeout",
        default=DEFAULT_EXIT_TIMEOUT,
        type=float,
        help="time (in seconds) to wait for the IOC to exit after sending exit",
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
            "raise if regex PATTERN matches output (may be given multiple times);"
            " built-in default: ^ERROR"
        ),
    )

    parser.add_argument(
        "--no-default-fail-on",
        action="store_true",
        default=False,
        dest="no_default_fail_on",
        help="disable the built-in ^ERROR pattern check",
    )

    return parser.parse_known_args(args)


def main() -> None:  # noqa: D103
    namespace, extra = parse_arguments()
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s ", level=logging.DEBUG
    )
    try:
        run_iocsh(
            *extra,
            delay=namespace.delay,
            timeout=namespace.timeout,
            executable=namespace.executable,
            fail_on=namespace.fail_on or None,
            no_builtin_fail_on=namespace.no_default_fail_on,
        )
    except (RunIocshError, FileNotFoundError):
        log.exception("Found an error")
        sys.exit(1)
