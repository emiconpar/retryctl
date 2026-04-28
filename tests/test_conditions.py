"""Tests for retryctl.conditions."""
import pytest

from retryctl.conditions import RetryCondition, build_condition


class TestShouldRetryOnSuccess:
    def test_zero_returncode_never_retried(self):
        cond = RetryCondition(retry_on_any_error=True)
        assert cond.should_retry(0) is False


class TestRetryOnCodes:
    def setup_method(self):
        self.cond = RetryCondition(retry_on_codes=[1, 2, 3])

    def test_matching_code_retried(self):
        assert self.cond.should_retry(1) is True

    def test_non_matching_code_not_retried(self):
        assert self.cond.should_retry(5) is False

    def test_zero_not_retried_even_if_listed(self):
        cond = RetryCondition(retry_on_codes=[0, 1])
        assert cond.should_retry(0) is False


class TestRetryOnAnyError:
    def setup_method(self):
        self.cond = RetryCondition(retry_on_any_error=True)

    def test_any_nonzero_code_retried(self):
        for code in [1, 2, 127, 255]:
            assert self.cond.should_retry(code) is True

    def test_zero_still_not_retried(self):
        assert self.cond.should_retry(0) is False


class TestSignalHandling:
    def test_fatal_signal_not_retried_by_default(self):
        # SIGKILL is signal 9; returncode -9 from subprocess
        cond = RetryCondition(retry_on_any_error=True, never_retry_on_signals=True)
        assert cond.should_retry(-9) is False

    def test_non_fatal_signal_retried_when_any_error(self):
        # SIGUSR1 is signal 10 — non-fatal, so retriable
        cond = RetryCondition(retry_on_any_error=True, never_retry_on_signals=True)
        assert cond.should_retry(-10) is True

    def test_signal_retried_when_never_retry_on_signals_false(self):
        cond = RetryCondition(retry_on_any_error=True, never_retry_on_signals=False)
        assert cond.should_retry(-9) is True


class TestBuildCondition:
    def test_returns_retry_condition(self):
        cond = build_condition(retry_on_codes=[1])
        assert isinstance(cond, RetryCondition)

    def test_defaults_to_empty_codes(self):
        cond = build_condition()
        assert cond.should_retry(1) is False

    def test_retry_on_any_error_propagated(self):
        cond = build_condition(retry_on_any_error=True)
        assert cond.should_retry(42) is True

    def test_codes_propagated(self):
        cond = build_condition(retry_on_codes=[7])
        assert cond.should_retry(7) is True
        assert cond.should_retry(8) is False
