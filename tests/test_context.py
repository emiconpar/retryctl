"""Tests for retryctl.context.RetryContext."""
import pytest
from retryctl.context import RetryContext


def _make_ctx(**kwargs) -> RetryContext:
    defaults = dict(command=["echo", "hi"], max_attempts=3)
    defaults.update(kwargs)
    return RetryContext(**defaults)


class TestAttemptsRemaining:
    def test_full_remaining_before_any_attempt(self):
        ctx = _make_ctx(max_attempts=5, attempt=0)
        assert ctx.attempts_remaining == 5

    def test_decrements_with_attempt(self):
        ctx = _make_ctx(max_attempts=3, attempt=2)
        assert ctx.attempts_remaining == 1

    def test_never_negative(self):
        ctx = _make_ctx(max_attempts=2, attempt=10)
        assert ctx.attempts_remaining == 0


class TestIsFinalAttempt:
    def test_not_final_when_attempts_remain(self):
        ctx = _make_ctx(max_attempts=3, attempt=1)
        assert not ctx.is_final_attempt

    def test_final_when_attempt_equals_max(self):
        ctx = _make_ctx(max_attempts=3, attempt=3)
        assert ctx.is_final_attempt

    def test_final_when_attempt_exceeds_max(self):
        ctx = _make_ctx(max_attempts=3, attempt=5)
        assert ctx.is_final_attempt


class TestDelayTracking:
    def test_total_delay_starts_at_zero(self):
        ctx = _make_ctx()
        assert ctx.total_delay == 0.0

    def test_record_delay_accumulates(self):
        ctx = _make_ctx()
        ctx.record_delay(1.5)
        ctx.record_delay(3.0)
        assert ctx.total_delay == pytest.approx(4.5)

    def test_delays_list_preserved_in_order(self):
        ctx = _make_ctx()
        ctx.record_delay(0.5)
        ctx.record_delay(1.0)
        ctx.record_delay(2.0)
        assert ctx.delays == [0.5, 1.0, 2.0]


class TestAsDict:
    def test_contains_expected_keys(self):
        ctx = _make_ctx(attempt=1, last_exit_code=1)
        d = ctx.as_dict()
        for key in (
            "command", "max_attempts", "attempt", "attempts_remaining",
            "last_exit_code", "last_error", "elapsed", "total_delay",
            "is_final_attempt",
        ):
            assert key in d

    def test_values_reflect_state(self):
        ctx = _make_ctx(max_attempts=4, attempt=2, last_exit_code=2, elapsed=1.234)
        ctx.record_delay(0.5)
        d = ctx.as_dict()
        assert d["attempt"] == 2
        assert d["attempts_remaining"] == 2
        assert d["last_exit_code"] == 2
        assert d["elapsed"] == pytest.approx(1.234, abs=1e-3)
        assert d["total_delay"] == pytest.approx(0.5)

    def test_elapsed_rounded_to_four_places(self):
        ctx = _make_ctx(elapsed=1.23456789)
        assert ctx.as_dict()["elapsed"] == 1.2346
