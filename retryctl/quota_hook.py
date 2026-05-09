"""Hook integration for RetryQuota: enforce quota before each retry."""
from __future__ import annotations

from retryctl.hooks import HookRegistry
from retryctl.hooks import HookContext
from retryctl.executor import ExecutionResult
from retryctl.quota import RetryQuota


def attach_quota_hooks(registry: HookRegistry, quota: RetryQuota) -> None:
    """Register quota enforcement on the on_retry hook."""
    registry.register_on_retry(_make_on_retry(quota))


def _make_on_retry(quota: RetryQuota):
    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        # Raises QuotaExceeded if the budget is exhausted; the executor
        # is expected to treat this as a terminal condition.
        quota.check_and_record()

    return _on_retry
