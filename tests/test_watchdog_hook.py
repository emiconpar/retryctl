"""Tests for retryctl.watchdog_hook."""
from __future__ import annotations

import time
import pytest

from retryctl.hooks import HookRegistry
from retryctl.watchdog import WatchdogConfig, WatchdogTripped
from retryctl.watchdog_hook import attach_watchdog_hooks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(exit_code: int = 1):
    from retryctl.executor import ExecutionResult
    return ExecutionResult(
        succeeded=exit_code == 0,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
    )


def _make_ctx():
    from retryctl.context import RetryContext
    return RetryContext(max_attempts=3)


def _make_cfg(timeout: float = 0.05) -> WatchdogConfig:
    return WatchdogConfig(stall_timeout=timeout, key="hook-test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAttachWatchdogHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.cfg = _make_cfg(timeout=0.05)
        self.watchdog = attach_watchdog_hooks(self.registry, self.cfg)

    def test_returns_watchdog_instance(self):
        from retryctl.watchdog import Watchdog
        assert isinstance(self.watchdog, Watchdog)

    def test_on_retry_starts_watchdog(self):
        result, ctx = _make_result(), _make_ctx()
        self.registry.fire_on_retry(result, ctx)
        # watchdog should be running; stop it cleanly
        self.watchdog.stop()
        assert self.watchdog.tripped is False

    def test_on_success_stops_watchdog_without_trip(self):
        result, ctx = _make_result(exit_code=0), _make_ctx()
        self.registry.fire_on_retry(result, ctx)
        self.registry.fire_on_success(result, ctx)
        time.sleep(0.1)  # timer should already be cancelled
        assert self.watchdog.tripped is False

    def test_on_final_failure_raises_if_tripped(self):
        cfg = _make_cfg(timeout=0.03)
        registry = HookRegistry()
        watchdog = attach_watchdog_hooks(registry, cfg)
        result, ctx = _make_result(), _make_ctx()
        registry.fire_on_retry(result, ctx)
        time.sleep(0.08)  # let watchdog trip
        assert watchdog.tripped is True
        with pytest.raises(WatchdogTripped):
            registry.fire_on_final_failure(result, ctx)

    def test_on_final_failure_no_raise_if_not_tripped(self):
        result, ctx = _make_result(), _make_ctx()
        # never start watchdog — final failure without prior retry
        registry = HookRegistry()
        attach_watchdog_hooks(registry, self.cfg)
        registry.fire_on_final_failure(result, ctx)  # should not raise

    def test_on_attempt_failure_feeds_watchdog(self):
        result, ctx = _make_result(), _make_ctx()
        self.registry.fire_on_retry(result, ctx)
        time.sleep(0.03)
        self.registry.fire_on_attempt_failure(result, ctx)  # feeds timer
        time.sleep(0.03)  # still within refreshed window
        assert self.watchdog.tripped is False
        self.watchdog.stop()
