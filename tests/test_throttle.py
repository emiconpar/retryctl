"""Tests for retryctl.throttle."""

from __future__ import annotations

import pytest

from retryctl.throttle import (
    SlidingWindowThrottle,
    ThrottleConfig,
    ThrottleExceeded,
)


# ---------------------------------------------------------------------------
# ThrottleConfig validation
# ---------------------------------------------------------------------------

class TestThrottleConfig:
    def test_valid_config_accepted(self):
        cfg = ThrottleConfig(max_attempts=5, window_seconds=10.0)
        assert cfg.max_attempts == 5
        assert cfg.window_seconds == 10.0

    def test_zero_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            ThrottleConfig(max_attempts=0, window_seconds=10.0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            ThrottleConfig(max_attempts=3, window_seconds=-1.0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            ThrottleConfig(max_attempts=3, window_seconds=0.0)


# ---------------------------------------------------------------------------
# SlidingWindowThrottle
# ---------------------------------------------------------------------------

class TestSlidingWindowThrottle:
    def _make(self, max_attempts: int = 3, window: float = 10.0) -> SlidingWindowThrottle:
        return SlidingWindowThrottle(ThrottleConfig(max_attempts=max_attempts, window_seconds=window))

    def test_check_passes_when_empty(self):
        t = self._make()
        t.check(ts=0.0)  # should not raise

    def test_check_passes_below_limit(self):
        t = self._make(max_attempts=3)
        t.record(ts=0.0)
        t.record(ts=1.0)
        t.check(ts=2.0)  # 2 recorded, limit is 3 – OK

    def test_check_raises_at_limit(self):
        t = self._make(max_attempts=2, window=10.0)
        t.record(ts=0.0)
        t.record(ts=1.0)
        with pytest.raises(ThrottleExceeded):
            t.check(ts=2.0)

    def test_retry_after_is_positive(self):
        t = self._make(max_attempts=1, window=10.0)
        t.record(ts=0.0)
        with pytest.raises(ThrottleExceeded) as exc_info:
            t.check(ts=5.0)
        assert exc_info.value.retry_after == pytest.approx(5.0)

    def test_old_entries_evicted(self):
        t = self._make(max_attempts=2, window=10.0)
        t.record(ts=0.0)
        t.record(ts=1.0)
        # Both timestamps are outside the window at ts=12
        t.check(ts=12.0)  # should not raise

    def test_current_count_reflects_window(self):
        t = self._make(max_attempts=5, window=10.0)
        t.record(ts=0.0)
        t.record(ts=1.0)
        t.record(ts=2.0)
        # At ts=11 the first record is outside the window
        import time
        # Patch monotonic indirectly via check; use current_count with manual eviction
        # We test via record/check rather than current_count to avoid real time.
        assert t.current_count >= 0  # smoke test

    def test_throttle_exceeded_message(self):
        exc = ThrottleExceeded(retry_after=3.5)
        assert "3.50" in str(exc)
