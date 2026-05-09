"""Tests for retryctl.quota_hook."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult
from retryctl.quota import QuotaConfig, QuotaExceeded, RetryQuota
from retryctl.quota_hook import attach_quota_hooks


def _make_result() -> ExecutionResult:
    return ExecutionResult(
        succeeded=False,
        returncode=1,
        stdout="",
        stderr="",
        attempts=1,
    )


def _make_ctx() -> HookContext:
    ctx = MagicMock(spec=HookContext)
    ctx.attempt = 1
    return ctx


def _make_quota(max_retries: int = 5) -> RetryQuota:
    cfg = QuotaConfig(key="hook-test", max_retries=max_retries, window_seconds=60.0)
    return RetryQuota(cfg)


class TestAttachQuotaHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.quota = _make_quota(max_retries=3)
        attach_quota_hooks(self.registry, self.quota)

    def test_on_retry_records_usage(self):
        result = _make_result()
        ctx = _make_ctx()
        self.registry.fire_on_retry(result, ctx)
        assert self.quota.current_usage() == 1

    def test_on_retry_multiple_times_accumulates(self):
        result = _make_result()
        ctx = _make_ctx()
        self.registry.fire_on_retry(result, ctx)
        self.registry.fire_on_retry(result, ctx)
        assert self.quota.current_usage() == 2

    def test_on_retry_raises_when_quota_exceeded(self):
        result = _make_result()
        ctx = _make_ctx()
        # exhaust the quota
        for _ in range(3):
            self.registry.fire_on_retry(result, ctx)
        with pytest.raises(QuotaExceeded):
            self.registry.fire_on_retry(result, ctx)

    def test_attempt_failure_hook_not_registered(self):
        """Quota hook should only touch on_retry, not attempt_failure."""
        initial = self.quota.current_usage()
        result = _make_result()
        ctx = _make_ctx()
        self.registry.fire_on_attempt_failure(result, ctx)
        assert self.quota.current_usage() == initial
