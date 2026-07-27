"""Exception classes for run-iocsh."""


class RunIocshError(Exception):
    """Base class for exceptions in this module."""


class IocshStateError(RunIocshError):
    """Exception raised for programming errors (wrong state transitions)."""


class IocshAlreadyRunningError(IocshStateError):
    """Exception raised when IOC is started a second time."""


class IocshTimeoutError(RunIocshError, TimeoutError):
    """Exception raised when an operation did not complete within its timeout.

    Also a builtin ``TimeoutError``, so ``except TimeoutError`` keeps working
    while ``except RunIocshError`` catches every error this library raises.
    """


class IocshStartupError(RunIocshError):
    """Exception raised when IOC exits before the expected readiness pattern appears."""


class IocshExitedError(RunIocshError):
    """Exception raised when the IOC exits on its own before it is told to."""


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
