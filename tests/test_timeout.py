"""Tests for retryctl.timeout."""

from __future__ import annotations

import sys
import time

import pytest

from retryctl.timeout import (
    TimeoutConfig,
    TimeoutExpired,
    attempt_timeout,
    deadline_remaining,
)


# ---------------------------------------------------------------------------
# TimeoutConfig
# ---------------------------------------------------------------------------

class TestTimeoutConfig:
    def test_none_values_allowed(self):
        cfg = TimeoutConfig()
        assert cfg.per_attempt is None
        assert cfg.total is None

    def test_positive_values_allowed(self):
        cfg = TimeoutConfig(per_attempt=5.0, total=30.0)
        assert cfg.per_attempt == 5.0
        assert cfg.total == 30.0

    def test_zero_per_attempt_raises(self):
        with pytest.raises(ValueError, match="per_attempt"):
            TimeoutConfig(per_attempt=0)

    def test_negative_total_raises(self):
        with pytest.raises(ValueError, match="total"):
            TimeoutConfig(total=-1.0)

    def test_zero_total_raises(self):
        with pytest.raises(ValueError, match="total"):
            TimeoutConfig(total=0)

    def test_negative_per_attempt_raises(self):
        with pytest.raises(ValueError, match="per_attempt"):
            TimeoutConfig(per_attempt=-0.5)


# ---------------------------------------------------------------------------
# attempt_timeout
# ---------------------------------------------------------------------------

@pytest.mark.skipif(sys.platform == "win32", reason="SIGALRM not available on Windows")
class TestAttemptTimeout:
    def test_no_timeout_completes_normally(self):
        with attempt_timeout(None):
            pass  # should not raise

    def test_completes_within_limit(self):
        with attempt_timeout(2.0):
            time.sleep(0.01)

    def test_raises_when_exceeded(self):
        with pytest.raises(TimeoutExpired) as exc_info:
            with attempt_timeout(0.05):
                time.sleep(5)
        assert exc_info.value.seconds == 0.05

    def test_timeout_message_contains_seconds(self):
        exc = TimeoutExpired(3.5)
        assert "3.5" in str(exc)

    def test_alarm_cleared_after_context(self):
        import signal
        with attempt_timeout(10.0):
            pass
        # Verify the alarm was cancelled (remaining time should be 0)
        remaining = signal.getitimer(signal.ITIMER_REAL)[0]
        assert remaining == 0.0

    def test_alarm_cleared_after_exception(self):
        """Ensure the alarm is cancelled even when a non-timeout exception occurs."""
        import signal
        with pytest.raises(RuntimeError):
            with attempt_timeout(10.0):
                raise RuntimeError("unexpected error")
        remaining = signal.getitimer(signal.ITIMER_REAL)[0]
        assert remaining == 0.0


# ---------------------------------------------------------------------------
# deadline_remaining
# ---------------------------------------------------------------------------

class TestDeadlineRemaining:
    def test_no_total_returns_none(self):
        assert deadline_remaining(0.0, None, 5.0) is None

    def test_returns_remaining_seconds(self):
        result = deadline_remaining(0.0, 10.0, 3.0)
        assert result == pytest.approx(7.0)

    def test_clamps_to_zero_when_overrun(self):
        result = deadline_remaining(0.0, 10.0, 15.0)
        assert result == 0.0
