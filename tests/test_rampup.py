"""Tests for retryctl.rampup."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from retryctl.rampup import (
    RampUpConfig,
    RampUpExceeded,
    RampUpState,
)
from retryctl.rampup_hook import attach_rampup_hooks
from retryctl.hooks import HookRegistry


def _make_state(initial=2, maximum=6, step=2, interval=10.0, clock=None):
    cfg = RampUpConfig(
        initial_limit=initial,
        max_limit=maximum,
        step=step,
        step_interval=interval,
        key="test",
    )
    state = RampUpState(config=cfg)
    if clock is not None:
        state._clock = clock
    return state


class TestRampUpConfig:
    def test_valid_config_accepted(self):
        cfg = RampUpConfig(initial_limit=1, max_limit=10, step=2, step_interval=5.0)
        assert cfg.initial_limit == 1

    def test_zero_initial_limit_raises(self):
        with pytest.raises(ValueError, match="initial_limit"):
            RampUpConfig(initial_limit=0, max_limit=10, step=1, step_interval=1.0)

    def test_max_less_than_initial_raises(self):
        with pytest.raises(ValueError, match="max_limit"):
            RampUpConfig(initial_limit=5, max_limit=3, step=1, step_interval=1.0)

    def test_zero_step_raises(self):
        with pytest.raises(ValueError, match="step"):
            RampUpConfig(initial_limit=1, max_limit=10, step=0, step_interval=1.0)

    def test_zero_interval_raises(self):
        with pytest.raises(ValueError, match="step_interval"):
            RampUpConfig(initial_limit=1, max_limit=10, step=1, step_interval=0.0)

    def test_blank_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            RampUpConfig(initial_limit=1, max_limit=10, step=1, step_interval=1.0, key="  ")


class TestRampUpState:
    def test_initial_limit_respected(self):
        fake_clock = MagicMock(return_value=0.0)
        state = _make_state(initial=2, clock=fake_clock)
        state.check()  # attempt 1 — ok
        state.check()  # attempt 2 — ok
        with pytest.raises(RampUpExceeded):
            state.check()  # attempt 3 — over limit

    def test_limit_increases_after_step_interval(self):
        tick = [0.0]
        def fake_clock():
            return tick[0]
        state = _make_state(initial=2, maximum=6, step=2, interval=10.0, clock=fake_clock)
        state.check()
        state.check()
        # advance past one step interval
        tick[0] = 11.0
        state.check()  # attempt 3 — limit is now 4
        state.check()  # attempt 4 — still ok
        with pytest.raises(RampUpExceeded):
            state.check()  # attempt 5 — over new limit of 4

    def test_limit_capped_at_max(self):
        tick = [1000.0]
        state = _make_state(initial=2, maximum=6, step=2, interval=1.0, clock=lambda: tick[0])
        assert state.current_limit == 6

    def test_reset_clears_attempt_count(self):
        fake_clock = MagicMock(return_value=0.0)
        state = _make_state(initial=2, clock=fake_clock)
        state.check()
        state.check()
        state.reset()
        state.check()  # should not raise


class TestAttachRampUpHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.state = _make_state(initial=2)
        attach_rampup_hooks(self.registry, self.state)

    def _make_args(self):
        result = MagicMock()
        ctx = MagicMock()
        return result, ctx

    def test_on_retry_increments_and_raises_when_exceeded(self):
        r, c = self._make_args()
        self.registry.fire_on_retry(r, c)  # 1
        self.registry.fire_on_retry(r, c)  # 2
        with pytest.raises(RampUpExceeded):
            self.registry.fire_on_retry(r, c)  # 3

    def test_on_success_resets_state(self):
        r, c = self._make_args()
        self.registry.fire_on_retry(r, c)
        self.registry.fire_on_retry(r, c)
        self.registry.fire_on_success(r, c)  # reset
        self.registry.fire_on_retry(r, c)  # should not raise
