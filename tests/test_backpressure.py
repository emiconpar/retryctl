"""Tests for retryctl.backpressure and retryctl.backpressure_hook."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from retryctl.backpressure import (
    BackpressureConfig,
    BackpressureState,
    BackpressureTripped,
)
from retryctl.backpressure_hook import attach_backpressure_hooks
from retryctl.hooks import HookRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(max_pressure: float = 0.8, hold_duration: float = 5.0) -> BackpressureState:
    cfg = BackpressureConfig(max_pressure=max_pressure, hold_duration=hold_duration)
    return BackpressureState(config=cfg)


def _make_result(exit_code: int = 1):
    r = MagicMock()
    r.exit_code = exit_code
    return r


def _make_ctx():
    return MagicMock()


# ---------------------------------------------------------------------------
# BackpressureConfig
# ---------------------------------------------------------------------------

class TestBackpressureConfig:
    def test_valid_config_accepted(self):
        cfg = BackpressureConfig(max_pressure=0.9, hold_duration=3.0, key="svc")
        assert cfg.max_pressure == 0.9

    def test_zero_max_pressure_raises(self):
        with pytest.raises(ValueError, match="max_pressure"):
            BackpressureConfig(max_pressure=0.0)

    def test_negative_max_pressure_raises(self):
        with pytest.raises(ValueError):
            BackpressureConfig(max_pressure=-0.1)

    def test_zero_hold_duration_raises(self):
        with pytest.raises(ValueError, match="hold_duration"):
            BackpressureConfig(hold_duration=0.0)

    def test_blank_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            BackpressureConfig(key="   ")


# ---------------------------------------------------------------------------
# BackpressureState
# ---------------------------------------------------------------------------

class TestBackpressureState:
    def test_initial_pressure_is_zero(self):
        state = _make_state()
        assert state.current_pressure == 0.0

    def test_not_active_initially(self):
        state = _make_state()
        assert not state.is_active()

    def test_update_sets_pressure(self):
        state = _make_state(max_pressure=0.8)
        state.update(0.5)
        assert state.current_pressure == 0.5

    def test_exceeding_threshold_trips_state(self):
        state = _make_state(max_pressure=0.5)
        state.update(0.9)
        assert state.is_active()

    def test_check_raises_when_active(self):
        state = _make_state(max_pressure=0.5)
        state.update(0.9)
        with pytest.raises(BackpressureTripped) as exc_info:
            state.check()
        assert exc_info.value.pressure == pytest.approx(0.9)

    def test_check_does_not_raise_below_threshold(self):
        state = _make_state(max_pressure=0.8)
        state.update(0.5)
        state.check()  # should not raise

    def test_hold_expires_after_duration(self):
        fake_clock = MagicMock(side_effect=[0.0, 0.0, 10.0])
        state = _make_state(max_pressure=0.5, hold_duration=5.0)
        state._clock = fake_clock
        state.update(0.9)       # trips at t=0
        assert state.is_active()  # t=0, elapsed=0 < 5
        assert not state.is_active()  # t=10, elapsed=10 >= 5

    def test_invalid_pressure_value_raises(self):
        state = _make_state()
        with pytest.raises(ValueError):
            state.update(1.5)


# ---------------------------------------------------------------------------
# backpressure_hook
# ---------------------------------------------------------------------------

class TestAttachBackpressureHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.state = _make_state(max_pressure=0.5, hold_duration=60.0)
        attach_backpressure_hooks(self.registry, self.state)

    def test_attempt_failure_accumulates_pressure(self):
        result = _make_result(exit_code=1)
        ctx = _make_ctx()
        self.registry.fire_on_attempt_failure(result, ctx)
        assert self.state.current_pressure == pytest.approx(0.1)

    def test_zero_exit_does_not_increase_pressure(self):
        result = _make_result(exit_code=0)
        ctx = _make_ctx()
        self.registry.fire_on_attempt_failure(result, ctx)
        assert self.state.current_pressure == pytest.approx(0.0)

    def test_on_retry_raises_when_tripped(self):
        self.state.update(0.9)  # exceed threshold
        result = _make_result()
        ctx = _make_ctx()
        with pytest.raises(BackpressureTripped):
            self.registry.fire_on_retry(result, ctx)

    def test_on_retry_passes_when_not_tripped(self):
        result = _make_result(exit_code=0)
        ctx = _make_ctx()
        self.registry.fire_on_retry(result, ctx)  # should not raise
