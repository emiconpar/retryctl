"""Tests for retryctl.bulkhead_hook."""
from __future__ import annotations

import pytest

from retryctl.bulkhead import BulkheadConfig, BulkheadFull, BulkheadRegistry
from retryctl.bulkhead_hook import attach_bulkhead_hooks
from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult


def _make_result(exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        succeeded=exit_code == 0,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        total_delay=0.0,
    )


def _make_ctx() -> HookContext:
    return HookContext(attempt=1, max_attempts=3, metadata={})


class TestAttachBulkheadHooks:
    def setup_method(self):
        self.registry = BulkheadRegistry()
        self.hooks = HookRegistry()
        self.config = BulkheadConfig(key="test", max_concurrent=2, queue_timeout=0.0)
        attach_bulkhead_hooks(self.hooks, self.config, registry=self.registry)

    def test_on_retry_acquires_slot(self):
        ctx = _make_ctx()
        self.hooks.fire_on_retry(_make_result(), ctx)
        assert self.registry.active_count("test") == 1

    def test_on_attempt_failure_releases_slot(self):
        ctx = _make_ctx()
        self.hooks.fire_on_retry(_make_result(), ctx)
        self.hooks.fire_on_attempt_failure(_make_result(), ctx)
        assert self.registry.active_count("test") == 0

    def test_on_final_failure_releases_slot(self):
        ctx = _make_ctx()
        self.hooks.fire_on_retry(_make_result(), ctx)
        self.hooks.fire_on_final_failure(_make_result(), ctx)
        assert self.registry.active_count("test") == 0

    def test_on_success_releases_slot(self):
        ctx = _make_ctx()
        self.hooks.fire_on_retry(_make_result(), ctx)
        self.hooks.fire_on_success(_make_result(exit_code=0), ctx)
        assert self.registry.active_count("test") == 0

    def test_raises_bulkhead_full_when_limit_exceeded(self):
        config = BulkheadConfig(key="tight", max_concurrent=1, queue_timeout=0.0)
        hooks = HookRegistry()
        attach_bulkhead_hooks(hooks, config, registry=self.registry)
        # Manually fill the partition
        partition = self.registry.get_or_create("tight", 1)
        partition.acquire(timeout=0)
        ctx = _make_ctx()
        with pytest.raises(BulkheadFull):
            hooks.fire_on_retry(_make_result(), ctx)

    def test_release_not_called_if_not_acquired(self):
        # attempt_failure without prior retry should not raise
        ctx = _make_ctx()
        self.hooks.fire_on_attempt_failure(_make_result(), ctx)  # no-op
        assert self.registry.active_count("test") == 0
