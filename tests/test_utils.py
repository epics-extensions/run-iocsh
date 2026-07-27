import pytest

from run_iocsh import IocshTimeoutError, RunIocshError, wait_for


class TestWaitFor:
    def test_returns_when_predicate_true(self) -> None:
        wait_for(lambda: True, timeout=1.0)

    def test_raises_on_timeout(self) -> None:
        with pytest.raises(TimeoutError):
            wait_for(lambda: False, timeout=0.05, poll_interval=0.01)

    def test_raises_the_library_timeout_type(self) -> None:
        with pytest.raises(IocshTimeoutError):
            wait_for(lambda: False, timeout=0.05, poll_interval=0.01)

    def test_library_timeout_is_still_a_builtin_timeout_error(self) -> None:
        # Subclassing the builtin keeps `except TimeoutError` callers working.
        assert issubclass(IocshTimeoutError, TimeoutError)
        assert issubclass(IocshTimeoutError, RunIocshError)

    def test_swallows_predicate_exceptions(self) -> None:
        call_count = 0

        def flaky() -> bool:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = "not ready yet"
                raise RuntimeError(msg)
            return True

        wait_for(flaky, timeout=1.0, poll_interval=0.01)
        assert call_count >= 3

    def test_none_timeout_polls_until_predicate_is_true(self) -> None:
        # None means wait forever, as it does throughout the stdlib.
        calls = []

        def ready() -> bool:
            calls.append(1)
            return len(calls) >= 3

        wait_for(ready, timeout=None, poll_interval=0.01)
        assert len(calls) == 3

    def test_zero_timeout_evaluates_the_predicate_once(self) -> None:
        calls = []

        def never() -> bool:
            calls.append(1)
            return False

        with pytest.raises(TimeoutError):
            wait_for(never, timeout=0)
        assert len(calls) == 1

    def test_timeout_message_contains_duration(self) -> None:
        with pytest.raises(TimeoutError, match=r"0\.05s"):
            wait_for(lambda: False, timeout=0.05, poll_interval=0.01)
