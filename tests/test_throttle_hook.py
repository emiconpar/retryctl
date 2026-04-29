"""Tests for retryctl.throttle_hook."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from retryctl.executor import ExecutionResult
from retryctl.hooks import HookContext, HookRegistry
from retryctl.throttle import SlidingWindowThrottle, ThrottleConfig, ThrottleExceeded
from retryctl.throttle_hook import attach_throttle_hooks


def _make_result(exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        succeeded=exit_code == 0,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        total_duration=0.1,
    )


def _make_ctx(attempt: int = 1) -> HookContext:
    return HookContext(attempt=attempt, result=_make_result(), delay=0.0)


class TestAttachThrottleHooks:
    def _make_throttle(self, max_attempts: int = 5, window: float = 60.0) -> SlidingWindowThrottle:
        return SlidingWindowThrottle(ThrottleConfig(max_attempts=max_attempts, window_seconds=window))

    def test_attempt_failure_records_in_throttle(self):
        throttle = self._make_throttle()
        registry = HookRegistry()
        attach_throttle_hooks(registry, throttle)

        assert throttle.current_count == 0
        registry.on_attempt_failure(_make_ctx())
        assert throttle.current_count == 1

    def test_retry_check_passes_when_under_limit(self):
        throttle = self._make_throttle(max_attempts=5)
        registry = HookRegistry()
        attach_throttle_hooks(registry, throttle)
        # Should not raise
        registry.on_retry(_make_ctx())

    def test_retry_raises_when_throttle_exceeded(self):
        throttle = self._make_throttle(max_attempts=1, window=60.0)
        registry = HookRegistry()
        attach_throttle_hooks(registry, throttle)

        # Fill the window
        throttle.record()

        with patch("retryctl.throttle_hook.time.sleep") as mock_sleep:
            with pytest.raises(ThrottleExceeded):
                registry.on_retry(_make_ctx())
            mock_sleep.assert_called_once()

    def test_sleep_duration_matches_retry_after(self):
        throttle = self._make_throttle(max_attempts=1, window=30.0)
        registry = HookRegistry()
        attach_throttle_hooks(registry, throttle)

        now = 5.0
        throttle.record(ts=0.0)

        with patch("retryctl.throttle_hook.time.sleep") as mock_sleep:
            with patch.object(throttle, "check", side_effect=ThrottleExceeded(retry_after=7.5)):
                with pytest.raises(ThrottleExceeded):
                    registry.on_retry(_make_ctx())
            mock_sleep.assert_called_once_with(7.5)

    def test_multiple_failures_accumulate(self):
        throttle = self._make_throttle(max_attempts=10)
        registry = HookRegistry()
        attach_throttle_hooks(registry, throttle)

        for i in range(4):
            registry.on_attempt_failure(_make_ctx(attempt=i + 1))

        assert throttle.current_count == 4
