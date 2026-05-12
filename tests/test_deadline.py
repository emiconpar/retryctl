"""Tests for retryctl.deadline and retryctl.deadline_hook."""
from __future__ import annotations

import pytest

from retryctl.deadline import DeadlineConfig, DeadlineExceeded, DeadlineState
from retryctl.deadline_hook import attach_deadline_hooks
from retryctl.hooks import HookRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def _make_state(max_duration: float, clock: _FakeClock) -> DeadlineState:
    cfg = DeadlineConfig(max_duration=max_duration, clock=clock)
    return DeadlineState(config=cfg)


# ---------------------------------------------------------------------------
# TestDeadlineConfig
# ---------------------------------------------------------------------------

class TestDeadlineConfig:
    def test_valid_config_accepted(self):
        cfg = DeadlineConfig(max_duration=10.0)
        assert cfg.max_duration == 10.0

    def test_zero_max_duration_raises(self):
        with pytest.raises(ValueError, match="max_duration"):
            DeadlineConfig(max_duration=0)

    def test_negative_max_duration_raises(self):
        with pytest.raises(ValueError, match="max_duration"):
            DeadlineConfig(max_duration=-1.0)


# ---------------------------------------------------------------------------
# TestDeadlineState
# ---------------------------------------------------------------------------

class TestDeadlineState:
    def test_check_passes_before_deadline(self):
        clock = _FakeClock(0.0)
        state = _make_state(5.0, clock)
        clock.advance(3.0)
        state.check()  # should not raise

    def test_check_raises_at_deadline(self):
        clock = _FakeClock(0.0)
        state = _make_state(5.0, clock)
        clock.advance(5.0)
        with pytest.raises(DeadlineExceeded):
            state.check()

    def test_check_raises_past_deadline(self):
        clock = _FakeClock(0.0)
        state = _make_state(5.0, clock)
        clock.advance(7.5)
        with pytest.raises(DeadlineExceeded):
            state.check()

    def test_remaining_decreases_over_time(self):
        clock = _FakeClock(0.0)
        state = _make_state(10.0, clock)
        assert state.remaining() == pytest.approx(10.0)
        clock.advance(4.0)
        assert state.remaining() == pytest.approx(6.0)

    def test_elapsed_increases_over_time(self):
        clock = _FakeClock(0.0)
        state = _make_state(10.0, clock)
        clock.advance(3.5)
        assert state.elapsed() == pytest.approx(3.5)

    def test_deadline_exceeded_message_contains_overrun(self):
        clock = _FakeClock(0.0)
        state = _make_state(5.0, clock)
        clock.advance(8.0)
        with pytest.raises(DeadlineExceeded, match="exceeded"):
            state.check()


# ---------------------------------------------------------------------------
# TestDeadlineHook
# ---------------------------------------------------------------------------

class TestDeadlineHook:
    def setup_method(self):
        self.clock = _FakeClock(0.0)
        self.state = _make_state(5.0, self.clock)
        self.registry = HookRegistry()
        attach_deadline_hooks(self.registry, self.state)

    def test_on_retry_passes_within_deadline(self):
        self.clock.advance(2.0)
        self.registry.fire_on_retry(None, None)  # should not raise

    def test_on_retry_raises_past_deadline(self):
        self.clock.advance(6.0)
        with pytest.raises(DeadlineExceeded):
            self.registry.fire_on_retry(None, None)

    def test_on_attempt_failure_passes_within_deadline(self):
        self.clock.advance(1.0)
        self.registry.fire_on_attempt_failure(None, None)  # should not raise

    def test_on_attempt_failure_raises_past_deadline(self):
        self.clock.advance(10.0)
        with pytest.raises(DeadlineExceeded):
            self.registry.fire_on_attempt_failure(None, None)
