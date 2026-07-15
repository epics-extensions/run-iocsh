from pathlib import Path

import pytest

from run_iocsh import (
    IocshFileNotFoundError,
    IocshMissingSharedLibraryError,
    IocshModuleNotFoundError,
    IocshPatternMatchError,
    IocshProcessError,
    IocshTimeoutError,
    run_iocsh,
)
from run_iocsh.ioc import RE_BUILTIN_FAIL_ON

SCRIPTS = Path(__file__).parent / "scripts"


class TestExceptions:
    def test_run_iocsh_script_not_found(self) -> None:
        with pytest.raises(FileNotFoundError) as excinfo:
            run_iocsh(executable="foo")
        assert "No such file or directory: 'foo'" in str(excinfo.value)

    def test_nonzero_exit_raises(self) -> None:
        script = str(SCRIPTS / "iocsh-nonzero-exit.py")
        with pytest.raises(IocshProcessError, match="Return code: 1"):
            run_iocsh(delay=0, executable=script)

    def test_run_iocsh_cmd_file_not_found(self) -> None:
        filename = "does-not-exist.cmd"
        script = str(SCRIPTS / "iocsh-cant-open.py")
        with pytest.raises(IocshFileNotFoundError) as excinfo:
            run_iocsh(filename, executable=script, delay=0.1)
        assert f"No such file or directory: '{filename}'" in str(excinfo.value)

    def test_run_iocsh_module_not_found(self) -> None:
        script = str(SCRIPTS / "iocsh-module-not-found.py")
        with pytest.raises(IocshModuleNotFoundError) as excinfo:
            run_iocsh("-r", "foo", executable=script, delay=0)
        assert "Error loading module: foo" in str(excinfo.value)

    def test_run_iocsh_iocshload_file_not_found(self) -> None:
        nonexistent_file = "fake"
        script = str(SCRIPTS / "iocsh-file-not-exist.py")
        with pytest.raises(IocshFileNotFoundError) as excinfo:
            run_iocsh(executable=script, delay=0.1)
        assert f"No such file or directory: '{nonexistent_file}'" in str(excinfo.value)

    def test_missing_shared_lib(self) -> None:
        script = str(SCRIPTS / "iocsh-missing-shared-lib.py")
        with pytest.raises(IocshMissingSharedLibraryError) as excinfo:
            run_iocsh(executable=script, delay=0)
        assert str(excinfo.value) == "Missing shared library: 'liblib'"

    @pytest.mark.parametrize("name", ["iocsh-timeout.py", "iocsh-stdout-closed.py"])
    def test_run_iocsh_timeout_expired(self, name: str) -> None:
        with pytest.raises(IocshTimeoutError) as excinfo:
            run_iocsh(delay=0.1, timeout=0.5, executable=str(SCRIPTS / name))
        assert str(excinfo.value) == "Failed to send exit to the IOC"


class TestCheckOutputFailOn:
    def test_builtin_error_pattern_detected(self) -> None:
        script = str(SCRIPTS / "iocsh-error-output.py")
        with pytest.raises(IocshPatternMatchError, match="ERROR"):
            run_iocsh(delay=0.1, executable=script)

    def test_ansi_wrapped_error_pattern_detected(self) -> None:
        # EPICS wraps ERROR in ANSI escapes, so ^ERROR only matches once the
        # escapes are stripped from captured output.
        script = str(SCRIPTS / "iocsh-ansi-error.py")
        with pytest.raises(IocshPatternMatchError, match="ERROR"):
            run_iocsh(delay=0, executable=script)

    def test_anchored_pattern_matches_first_stderr_line(self) -> None:
        # Concatenating stdout + stderr glues the first stderr line onto the
        # last stdout line, which defeats the anchor.
        script = str(SCRIPTS / "iocsh-ansi-error.py")
        with pytest.raises(IocshPatternMatchError, match="DEBUG"):
            run_iocsh(delay=0, executable=script, fail_on=(r"^DEBUG: PID",))

    def test_user_fail_on_pattern_raises(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        with pytest.raises(IocshPatternMatchError, match="CUSTOM_ERROR:"):
            run_iocsh(delay=0.1, executable=script, fail_on=["CUSTOM_ERROR:"])

    def test_user_fail_on_no_match_does_not_raise(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        run_iocsh(delay=0.1, executable=script, fail_on=["WILL_NOT_MATCH"])

    def test_builtin_fail_on_is_exported(self) -> None:
        assert isinstance(RE_BUILTIN_FAIL_ON, str)
        assert "ERROR" in RE_BUILTIN_FAIL_ON

    def test_fail_on_replaces_default(self) -> None:
        # Passing fail_on= replaces DEFAULT_FAIL_ON; ^ERROR is no longer checked
        script = str(SCRIPTS / "iocsh-error-output.py")
        run_iocsh(delay=0.1, executable=script, fail_on=("WILL_NOT_MATCH",))
