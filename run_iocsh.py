#!/usr/bin/env python
# Copyright (c) 2019 European Spallation Source ERIC
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
import re
import subprocess
import time


RE_MODULE_NOT_AVAILABLE = re.compile("Module .*? not available")
RE_CANT_OPEN = re.compile(r"(save_restore:)?\s*Can't\s*open\s*(.*?):")


class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class IocshModuleNotFoundError(Error):
    """Exception raised when the required module is not found"""

    pass


class IocshProcessError(Error):
    """Exception raised when the iocsh script exits with a non null return code

    Only raised if no error was catched (and another exception raised)
    """

    pass


def run_iocsh(name, delay, *args):
    """Run <name> iocsh script and send the exit command after <delay> seconds"""
    cmd = [name] + list(args)
    logging.debug(f"Running: {cmd}")
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(delay)
    try:
        outs, errs = proc.communicate(input=b"exit\n", timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs = proc.stdout.read()
        errs = proc.stderr.read()
    outs = outs.decode("utf-8")
    errs = errs.decode("utf-8")
    logging.info(
        "========== stdout ============================\n"
        + outs
        + "============================================================================"
    )
    logging.info(
        "========== stderr ============================\n"
        + errs
        + "============================================================================"
    )
    logging.debug(f"return code: {proc.returncode}")
    m = RE_MODULE_NOT_AVAILABLE.search(outs)
    if m:
        raise IocshModuleNotFoundError(m.group(0))
    m = RE_CANT_OPEN.search(outs)
    if m and m.group(1) != "save_restore:":
        raise FileNotFoundError(f"No such file or directory: '{m.group(2)}'")
    if proc.returncode != 0:
        raise IocshProcessError(f"Return code: {proc.returncode}")


def main():
    """Entry point"""
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s ", level=logging.DEBUG
    )
    parser = argparse.ArgumentParser(
        description="Run iocsch.bash and send the exit command after x seconds"
    )
    parser.add_argument(
        "--name",
        help="name of the iocsh script [default: iocsh.bash]",
        default="iocsh.bash",
    )
    parser.add_argument(
        "--delay",
        help="time (in seconds) to wait before to send the exit command [default: 5]",
        type=int,
        default=5,
    )
    args, remaining = parser.parse_known_args()
    run_iocsh(args.name, args.delay, *remaining)


if __name__ == "__main__":
    main()
