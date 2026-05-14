"""Tests for retryctl.shedding."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from retryctl.shedding import (
    SheddingConfig,
    SheddingState,
    LoadSheddingTripped,
    _read_cpu_load,
    _read_loadavg,
)
from retryctl.hooks import HookRegistry
from retryctl.shedding_hook import attach_shedding_hooks


# ---------------------------------------------------------------------------
# SheddingConfig
# ---------------------------------------------------------------------------

class TestSheddingConfig:
    def test_valid_cpu_config_accepted(self):
        cfg = SheddingConfig(threshold=0.8, load_source="cpu")
        assert cfg.threshold == 0.8

    def test_valid_loadavg_config_accepted(self):
        cfg = SheddingConfig(threshold=4.0, load_source="loadavg")
        assert cfg.load_source == "loadavg"

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold must be positive"):
            SheddingConfig(threshold=0.0)

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold must be positive"):
            SheddingConfig(threshold=-0.1)

    def test_cpu_threshold_above_one_raises(self):
        with pytest.raises(ValueError, match="cpu threshold"):
            SheddingConfig(threshold=1.5, load_source="cpu")

    def test_invalid_load_source_raises(self):
        with pytest.raises(ValueError, match="load_source"):
            SheddingConfig(threshold=0.5, load_source="disk")

    def test_zero_min_attempt_raises(self):
        with pytest.raises(ValueError, match="min_attempt"):
            SheddingConfig(threshold=0.5, min_attempt=0)


# ---------------------------------------------------------------------------
# SheddingState
# ---------------------------------------------------------------------------

def _make_state(threshold=0.75, source="cpu", min_attempt=1):
    cfg = SheddingConfig(threshold=threshold, load_source=source, min_attempt=min_attempt)
    return SheddingState(config=cfg)


class TestSheddingState:
    def test_no_trip_when_load_below_threshold(self):
        state = _make_state(threshold=0.9)
        with patch("retryctl.shedding._read_cpu_load", return_value=0.5):
            state.check(attempt_number=1)  # should not raise

    def test_trips_when_load_exceeds_threshold(self):
        state = _make_state(threshold=0.5)
        with patch("retryctl.shedding._read_cpu_load", return_value=0.8):
            with pytest.raises(LoadSheddingTripped) as exc_info:
                state.check(attempt_number=1)
        assert exc_info.value.current_load == pytest.approx(0.8)
        assert exc_info.value.threshold == pytest.approx(0.5)

    def test_shed_count_increments_on_trip(self):
        state = _make_state(threshold=0.5)
        with patch("retryctl.shedding._read_cpu_load", return_value=0.9):
            for _ in range(3):
                try:
                    state.check(attempt_number=2)
                except LoadSheddingTripped:
                    pass
        assert state.shed_count == 3

    def test_skips_check_before_min_attempt(self):
        state = _make_state(threshold=0.1, min_attempt=3)
        with patch("retryctl.shedding._read_cpu_load", return_value=0.99):
            state.check(attempt_number=2)  # should not raise

    def test_uses_loadavg_source(self):
        state = _make_state(threshold=2.0, source="loadavg")
        with patch("retryctl.shedding._read_loadavg", return_value=5.0):
            with pytest.raises(LoadSheddingTripped):
                state.check(attempt_number=1)


# ---------------------------------------------------------------------------
# Hook integration
# ---------------------------------------------------------------------------

def _make_result():
    r = MagicMock()
    r.exit_code = 1
    return r


def _make_ctx(attempt=2):
    ctx = MagicMock()
    ctx.attempt = attempt
    return ctx


class TestAttachSheddingHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.state = _make_state(threshold=0.5)

    def test_on_retry_raises_when_overloaded(self):
        attach_shedding_hooks(self.registry, self.state)
        with patch("retryctl.shedding._read_cpu_load", return_value=0.9):
            with pytest.raises(LoadSheddingTripped):
                self.registry.fire_on_retry(_make_result(), _make_ctx())

    def test_on_attempt_failure_raises_when_overloaded(self):
        attach_shedding_hooks(self.registry, self.state)
        with patch("retryctl.shedding._read_cpu_load", return_value=0.9):
            with pytest.raises(LoadSheddingTripped):
                self.registry.fire_on_attempt_failure(_make_result(), _make_ctx())

    def test_no_raise_when_load_acceptable(self):
        attach_shedding_hooks(self.registry, self.state)
        with patch("retryctl.shedding._read_cpu_load", return_value=0.1):
            self.registry.fire_on_retry(_make_result(), _make_ctx())  # no raise
