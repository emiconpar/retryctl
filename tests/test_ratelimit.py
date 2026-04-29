"""Tests for retryctl.ratelimit and retryctl.ratelimit_hook."""

from __future__ import annotations

import time
import pytest

from retryctl.ratelimit import RateLimitConfig, RateLimitExceeded, SlidingWindowRateLimiter
from retryctl.ratelimit_hook import attach_ratelimit_hooks
from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------

class TestRateLimitConfig:
    def test_valid_config_accepted(self):
        cfg = RateLimitConfig(max_attempts=5, window_seconds=10.0)
        assert cfg.max_attempts == 5
        assert cfg.window_seconds == 10.0

    def test_zero_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RateLimitConfig(max_attempts=0, window_seconds=10.0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitConfig(max_attempts=3, window_seconds=-1.0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitConfig(max_attempts=3, window_seconds=0.0)


# ---------------------------------------------------------------------------
# SlidingWindowRateLimiter
# ---------------------------------------------------------------------------

class TestSlidingWindowRateLimiter:
    def _make(self, max_attempts: int = 3, window: float = 60.0) -> SlidingWindowRateLimiter:
        return SlidingWindowRateLimiter(RateLimitConfig(max_attempts=max_attempts, window_seconds=window))

    def test_initially_allowed(self):
        limiter = self._make(max_attempts=2)
        assert limiter.is_allowed() is True

    def test_allowed_up_to_limit(self):
        limiter = self._make(max_attempts=3)
        for _ in range(3):
            limiter.record()
        assert limiter.is_allowed() is False

    def test_current_count_reflects_records(self):
        limiter = self._make(max_attempts=5)
        limiter.record()
        limiter.record()
        assert limiter.current_count == 2

    def test_check_and_record_raises_when_exceeded(self):
        limiter = self._make(max_attempts=2)
        limiter.check_and_record()
        limiter.check_and_record()
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_and_record()
        assert exc_info.value.retry_after >= 0.0

    def test_rate_limit_exceeded_message(self):
        limiter = self._make(max_attempts=1)
        limiter.check_and_record()
        with pytest.raises(RateLimitExceeded, match="Rate limit exceeded"):
            limiter.check_and_record()


# ---------------------------------------------------------------------------
# attach_ratelimit_hooks
# ---------------------------------------------------------------------------

def _make_result() -> ExecutionResult:
    return ExecutionResult(
        succeeded=False, returncode=1, stdout="", stderr="", attempts=1
    )


def _make_ctx() -> HookContext:
    return HookContext(attempt=1, max_attempts=5, elapsed=0.1, command=["false"])


class TestAttachRateLimitHooks:
    def test_hook_registered_and_allows_when_under_limit(self):
        registry = HookRegistry()
        limiter = SlidingWindowRateLimiter(RateLimitConfig(max_attempts=3, window_seconds=60.0))
        attach_ratelimit_hooks(registry, limiter)
        # Should not raise
        registry.fire_on_retry(_make_result(), _make_ctx())
        assert limiter.current_count == 1

    def test_hook_raises_when_limit_exceeded(self):
        registry = HookRegistry()
        limiter = SlidingWindowRateLimiter(RateLimitConfig(max_attempts=1, window_seconds=60.0))
        attach_ratelimit_hooks(registry, limiter)
        registry.fire_on_retry(_make_result(), _make_ctx())  # first — OK
        with pytest.raises(RateLimitExceeded):
            registry.fire_on_retry(_make_result(), _make_ctx())  # second — exceeds
