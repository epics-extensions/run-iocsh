"""Exception classes for run-iocsh."""

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


class RunIocshError(Exception):
    """Base class for exceptions in this module."""


class IocshStateError(RunIocshError):
    """Exception raised for programming errors (wrong state transitions)."""


class IocshAlreadyRunningError(IocshStateError):
    """Exception raised when IOC is started a second time."""


class IocshTimeoutError(RunIocshError):
    """Exception raised when a timeout occurred trying to send exit to the IOC."""


class IocshStartupError(RunIocshError):
    """Exception raised when IOC exits before the expected readiness pattern appears."""


class IocshOutputError(RunIocshError):
    """Base exception for errors detected in IOC output."""


class IocshFileNotFoundError(IocshOutputError, FileNotFoundError):
    """Exception raised when a file referenced in the startup script is not found."""


class IocshModuleNotFoundError(IocshOutputError):
    """Exception raised when the required module is not found."""


class IocshMissingSharedLibraryError(IocshOutputError):
    """Exception raised when shared library is missing."""


class IocshProcessError(IocshOutputError):
    """Exception raised when the iocsh script exits with a non null return code."""


class IocshPatternMatchError(IocshOutputError):
    """Exception raised when a fail_on pattern matches the IOC output."""
