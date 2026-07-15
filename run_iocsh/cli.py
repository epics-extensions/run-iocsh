"""CLI entry point for package."""

import argparse
import logging
import sys

from run_iocsh.exceptions import RunIocshError
from run_iocsh.ioc import (
    DEFAULT_DELAY,
    DEFAULT_EXECUTABLE,
    DEFAULT_EXIT_TIMEOUT,
    DEFAULT_FAIL_ON,
    DEFAULT_INIT_PATTERN,
    DEFAULT_INIT_TIMEOUT,
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

    parser.add_argument(
        "--pattern",
        default=DEFAULT_INIT_PATTERN,
        help="regex to wait for before considering the IOC ready",
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
            delay=namespace.delay,
            exit_timeout=namespace.exit_timeout,
            init_timeout=namespace.init_timeout,
            pattern=namespace.pattern,
            executable=namespace.executable,
            fail_on=base + tuple(namespace.fail_on),
        )
    except (RunIocshError, FileNotFoundError):
        log.exception("Found an error")
        sys.exit(1)
