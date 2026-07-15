import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from run_iocsh.cli import main, parse_arguments

SCRIPTS = Path(__file__).parent / "scripts"


@pytest.mark.parametrize(
    "args",
    [
        ("--settle", "1", "nonexistent.cmd"),
        ("--exit-timeout", "1", "nonexistent.cmd"),
        ("--init-timeout", "1", "nonexistent.cmd"),
        ("--pattern", "ready", "nonexistent.cmd"),
        ("--no-wait-for-init", "nonexistent.cmd"),
        ("--executable", "iocsh", "nonexistent.cmd"),
        ("-r", "iocstats"),
        ("--unknown-flag", "value", "nonexistent.cmd"),
    ],
)
def test_parse_arguments_does_not_raise(args: tuple[str]) -> None:
    parse_arguments(args)


@pytest.mark.parametrize("flag", ["--delay", "--timeout"])
def test_renamed_flags_are_rejected(flag: str) -> None:
    # These were renamed. Silently forwarding them to the IOC would turn a typo
    # into an argument the IOC does not understand, or worse, one it does.
    with pytest.raises(SystemExit) as excinfo:
        parse_arguments([flag, "1", "st.cmd"])
    assert excinfo.value.code == 2


def test_pattern_and_no_wait_for_init_conflict() -> None:
    # Waiting for a pattern and skipping the wait cannot both be asked for.
    with pytest.raises(SystemExit) as excinfo:
        parse_arguments(["--pattern", "ready", "--no-wait-for-init", "st.cmd"])
    assert excinfo.value.code == 2


def test_no_wait_for_init_lands_on_its_name() -> None:
    # It can no longer ride along in test_arguments_land (it conflicts with
    # --pattern), so assert the flag parses on its own.
    namespace, _ = parse_arguments(["--no-wait-for-init", "st.cmd"])
    assert namespace.no_wait_for_init is True


def test_arguments_land_on_their_expected_names() -> None:
    # parse_known_args accepts anything, so unknown flags never raise -- assert
    # the values actually arrive rather than that parsing succeeded.
    namespace, extra = parse_arguments(
        [
            "--settle",
            "2",
            "--exit-timeout",
            "3",
            "--init-timeout",
            "4",
            "--pattern",
            "ready",
            "st.cmd",
        ]
    )
    assert namespace.settle == 2.0
    assert namespace.exit_timeout == 3.0
    assert namespace.init_timeout == 4.0
    assert namespace.pattern == "ready"
    assert extra == ["st.cmd"]


class TestMain:
    def test_success_exits_zero(self) -> None:
        script = str(SCRIPTS / "iocsh-print-and-exit.py")
        with patch.object(
            sys, "argv", ["run-iocsh", "--executable", script, "--settle", "0"]
        ):
            main()

    def test_ioc_dying_during_settle_exits_one(self) -> None:
        # The CLI settles by default, so an IOC that becomes ready and then
        # exits before the window is up is a failure.
        script = str(SCRIPTS / "iocsh-dies-after-ready.py")
        with patch.object(
            sys, "argv", ["run-iocsh", "--executable", script, "--settle", "1"]
        ):
            with pytest.raises(SystemExit) as excinfo:
                main()
        assert excinfo.value.code == 1

    def test_missing_executable_exits_one(self) -> None:
        with patch.object(sys, "argv", ["run-iocsh", "--executable", "does-not-exist"]):
            with pytest.raises(SystemExit) as excinfo:
                main()
        assert excinfo.value.code == 1

    def test_fail_on_pattern_exits_one(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        with patch.object(
            sys,
            "argv",
            ["run-iocsh", "--executable", script, "--fail-on", "CUSTOM_ERROR:"],
        ):
            with pytest.raises(SystemExit) as excinfo:
                main()
        assert excinfo.value.code == 1

    def test_fail_on_no_match_exits_zero(self) -> None:
        script = str(SCRIPTS / "iocsh-custom-error.py")
        with patch.object(
            sys,
            "argv",
            [
                "run-iocsh",
                "--executable",
                script,
                "--fail-on",
                "WILL_NOT_MATCH",
                "--settle",
                "0",
            ],
        ):
            main()
