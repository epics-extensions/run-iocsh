"""CLI entry point for package."""

# Copyright (c) 2024 European Spallation Source ERIC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import logging
import sys

from run_iocsh.ioc import RunIocshError, run_iocsh

log = logging.getLogger(__name__)


def parse_arguments(  # noqa: D103
    args: list[str] | None = None,
) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Run iocsh and send the exit command after <delay> seconds",
    )

    parser.add_argument(
        "--delay",
        default=5.0,
        type=float,
        help="time (in seconds) to wait before sending the exit command [default: 5]",
    )

    parser.add_argument(
        "--timeout",
        default=5,
        type=float,
        help="time (in seconds) to wait when sending the exit command [default: 5]",
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
        )
    except (RunIocshError, FileNotFoundError):
        log.exception("Found an error")
        sys.exit(1)
