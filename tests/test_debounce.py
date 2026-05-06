"""Tests for retryctl.debounce."""

from __future__ import annotations

import time

import pytest

from retryctl.debounce import DebounceConfig, DebounceState, DebounceViolation


# ---------------------------------------------------------------------------
# DebounceConfig validation
# ---------------------------------------------------------------------------

class TestDebounceConfig:
    def test_valid_config_accepted(self):
        cfg = DebounceConfig(min_interval=0.5, key="svc")
        assert cfg.min_interval == 0.5
        assert cfg.key == "svc"

    def test_zero_min_interval_raises(self):
        with pytest.raises(ValueError, match="min_interval"):
            DebounceConfig(min_interval=0.0)

    def test_negative_min_interval_raises(self):
        with pytest.raises(ValueError, match="min_interval"):
            DebounceConfig(min_interval=-1.0)

    def test_blank_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            DebounceConfig(min_interval=1.0, key="   ")

    def test_default_key_is_default(self):
        cfg = DebounceConfig(min_interval=1.0)
        assert cfg.key == "default"


# ---------------------------------------------------------------------------
# DebounceState behaviour
# ---------------------------------------------------------------------------

def _make_state(min_interval: float = 0.5) -> DebounceState:
    return DebounceState(config=DebounceConfig(min_interval=min_interval))


class TestDebounceState:
    def test_check_passes_before_any_record(self):
        state = _make_state()
        state.check()  # should not raise

    def test_is_ready_before_any_record(self):
        state = _make_state()
        assert state.is_ready() is True

    def test_seconds_until_ready_before_record(self):
        state = _make_state()
        assert state.seconds_until_ready() == 0.0

    def test_check_raises_immediately_after_record(self):
        state = _make_state(min_interval=10.0)
        state.record()
        with pytest.raises(DebounceViolation) as exc_info:
            state.check()
        assert exc_info.value.wait_remaining > 0

    def test_is_ready_false_immediately_after_record(self):
        state = _make_state(min_interval=10.0)
        state.record()
        assert state.is_ready() is False

    def test_seconds_until_ready_positive_after_record(self):
        state = _make_state(min_interval=10.0)
        state.record()
        remaining = state.seconds_until_ready()
        assert 0 < remaining <= 10.0

    def test_check_passes_after_interval_elapsed(self):
        state = _make_state(min_interval=0.05)
        state.record()
        time.sleep(0.07)
        state.check()  # should not raise

    def test_is_ready_true_after_interval_elapsed(self):
        state = _make_state(min_interval=0.05)
        state.record()
        time.sleep(0.07)
        assert state.is_ready() is True

    def test_debounce_violation_message_contains_wait(self):
        state = _make_state(min_interval=5.0)
        state.record()
        with pytest.raises(DebounceViolation, match="wait"):
            state.check()
