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
import subprocess
import time
import sys


def run_iocsh(name, delay, *args):
    """Run <name> iocsh script and send the exit command after <delay> seconds"""
    cmd = [name] + list(args)
    logging.debug("Running: {}".format(cmd))
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(delay)
    try:
        outs, errs = proc.communicate(input=b"exit\n", timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()
    logging.info(
        "========== stdout ============================\n"
        + outs.decode("utf-8")
        + "============================================================================"
    )
    logging.info(
        "========== stderr ============================\n"
        + errs.decode("utf-8")
        + "============================================================================"
    )
    logging.debug("return code: {}".format(proc.returncode))
    sys.exit(proc.returncode)


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
