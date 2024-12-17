"""Class, exceptions, and utility functions for running an IOC and capturing output."""

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

import logging
import re
import shutil
import subprocess
import time
from enum import Enum

RE_MODULE_NOT_AVAILABLE = re.compile("Module .*? not available")
RE_CANT_OPEN = re.compile(r"[Cc]an't\s*open\s*(.*?):")
RE_DOES_NOT_EXIST = re.compile(r"File (.*) does not exist")
RE_MISSING_SHARED_LIB = re.compile(r"(lib.*): cannot open shared object file")


class RunIocshError(Exception):
    """Base class for exceptions in this module."""


class IocshModuleNotFoundError(RunIocshError):
    """Exception raised when the required module is not found."""


class IocshProcessError(RunIocshError):
    """
    Exception raised when the iocsh script exits with a non null return code.

    Only raised if no error was catched (and another exception raised).
    """


class IocshTimeoutExpiredError(RunIocshError):
    """Exception raised when a timeout occurred trying to send exit to the softIOC."""


class IocshAlreadyRunningError(RunIocshError):
    """Exception raised when IOC is started a second time."""


class MissingSharedLibraryError(RunIocshError):
    """Exception raised when shared library is missing."""


class IOC:
    """Class to wrap IOC process."""

    state_values = Enum("state_values", "INITIALIZED STARTED EXITED")

    def __init__(
        self,
        *args: str,
        ioc_executable: str = "iocsh",
        timeout: float = 5.0,
    ) -> None:
        self.proc = None
        self.outs = ""
        self.errs = ""
        self.args = args
        if not shutil.which(ioc_executable):
            raise FileNotFoundError(f"No such file or directory: '{ioc_executable}'")
        self.ioc_executable = ioc_executable
        self.timeout = timeout
        self.state = self.state_values.INITIALIZED

    def __enter__(self) -> None:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        exc_traceback: object,
    ) -> None:
        self.exit()

    def is_running(self) -> bool:
        """Check if the ioc is already running."""
        return self.proc is not None and self.proc.poll() is None

    def start(self) -> None:
        """Run <self.ioc_executable> iocsh script with given command-line args."""
        if self.state == self.state_values.STARTED:
            raise IocshAlreadyRunningError("IOC already running")

        self.state = self.state_values.STARTED

        # Reset the output
        self.outs = ""
        self.errs = ""

        self._exited = False

        cmd = [str(item) for item in [self.ioc_executable, *self.args]]
        logging.debug("Running: %s", " ".join(cmd))
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    def exit(self) -> None:
        """Send the exit command to the running IOC."""
        if self.state != self.state_values.STARTED:
            logging.warning("IOC is not running")
            return

        self.state = self.state_values.EXITED

        try:
            outs, errs = self.proc.communicate(input=b"exit\n", timeout=self.timeout)
        except subprocess.TimeoutExpired as e:
            self.proc.kill()
            # Trying to run "outs, errs = proc.communicate()" can raise:
            # ValueError: Invalid file object: <_io.BufferedReader name=7>
            # when stdin is already closed.
            # In case of timeout, we don't care and just raise an exception
            raise IocshTimeoutExpiredError("Failed to send exit to the IOC") from e

        self.outs = outs.decode("utf-8")
        self.errs = errs.decode("utf-8")

    def check_output(self) -> None:
        """Log and check output from subprocess."""
        if self.state != self.state_values.EXITED:
            logging.warning("IOC has not exited yet")
            return

        logging.info(
            "========== stdout ============================\n"
            + self.outs
            + "=============================================="
        )
        logging.info(
            "========== stderr ============================\n"
            + self.errs
            + "=============================================="
        )
        logging.debug("return code: %s", self.proc.returncode)
        m = RE_MODULE_NOT_AVAILABLE.search(self.outs + self.errs)
        if m:
            raise IocshModuleNotFoundError(m.group(0))
        m1 = RE_CANT_OPEN.search(self.outs + self.errs)
        m2 = RE_DOES_NOT_EXIST.search(self.errs)
        if m1 or m2:
            raise FileNotFoundError(
                f"No such file or directory: '{m1.group(1) if m1 else m2.group(1)}'"
            )
        m = RE_MISSING_SHARED_LIB.search(self.outs + self.errs)
        if m:
            raise MissingSharedLibraryError(f"Missing shared library: '{m.group(1)}'")
        if self.proc.returncode != 0:
            raise IocshProcessError(f"Return code: {self.proc.returncode}\n{self.errs}")


def run_iocsh(name: str, delay: int, *args: str, timeout: float = 5) -> None:
    """Run an IOC, exit, and parse the output."""
    with IOC(*args, ioc_executable=name, timeout=timeout) as ioc:
        time.sleep(delay)
    ioc.check_output()
