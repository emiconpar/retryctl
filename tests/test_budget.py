"""Tests for retryctl.budget and retryctl.budget_hook."""
from __future__ import annotations

import time

import pytest

from retryctl.budget import BudgetConfig, BudgetExceeded, RetryBudget
from retryctl.budget_hook import attach_budget_hooks
from retryctl.hooks import HookRegistry


# ---------------------------------------------------------------------------
# BudgetConfig validation
# ---------------------------------------------------------------------------

class TestBudgetConfig:
    def test_valid_config_accepted(self):
        cfg = BudgetConfig(max_retries=5, window_seconds=60.0)
        assert cfg.max_retries == 5
        assert cfg.window_seconds == 60.0

    def test_zero_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries"):
            BudgetConfig(max_retries=0, window_seconds=60.0)

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries"):
            BudgetConfig(max_retries=-1, window_seconds=60.0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            BudgetConfig(max_retries=5, window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            BudgetConfig(max_retries=5, window_seconds=-1.0)


# ---------------------------------------------------------------------------
# RetryBudget behaviour
# ---------------------------------------------------------------------------

def _make_budget(max_retries: int = 3, window: float = 60.0) -> RetryBudget:
    return RetryBudget(config=BudgetConfig(max_retries=max_retries, window_seconds=window))


class TestRetryBudget:
    def test_initial_remaining_equals_max(self):
        budget = _make_budget(max_retries=3)
        assert budget.remaining() == 3

    def test_remaining_decrements_on_record(self):
        budget = _make_budget(max_retries=3)
        budget.check_and_record()
        assert budget.remaining() == 2

    def test_budget_exhausted_raises(self):
        budget = _make_budget(max_retries=2)
        budget.check_and_record()
        budget.check_and_record()
        with pytest.raises(BudgetExceeded):
            budget.check_and_record()

    def test_reset_clears_history(self):
        budget = _make_budget(max_retries=2)
        budget.check_and_record()
        budget.check_and_record()
        budget.reset()
        assert budget.remaining() == 2

    def test_expired_entries_evicted(self):
        budget = _make_budget(max_retries=2, window=0.05)
        budget.check_and_record()
        time.sleep(0.1)
        # After window expires the old entry should be gone
        assert budget.remaining() == 2

    def test_budget_exceeded_message_contains_limits(self):
        exc = BudgetExceeded(max_retries=5, window=30.0)
        assert "5" in str(exc)
        assert "30" in str(exc)


# ---------------------------------------------------------------------------
# budget_hook integration
# ---------------------------------------------------------------------------

class TestBudgetHook:
    def _make_ctx(self):
        from retryctl.hooks import HookContext
        from retryctl.context import RetryContext
        ctx = RetryContext(max_attempts=5)
        return HookContext(retry_ctx=ctx, command=["echo", "hi"])

    def _make_result(self, code: int = 1):
        from retryctl.executor import ExecutionResult
        return ExecutionResult(
            succeeded=False, returncode=code, stdout="", stderr="", attempts=1
        )

    def test_hook_records_retry(self):
        budget = _make_budget(max_retries=3)
        registry = HookRegistry()
        attach_budget_hooks(registry, budget)
        ctx = self._make_ctx()
        result = self._make_result()
        registry.fire_on_retry(result, ctx)
        assert budget.remaining() == 2

    def test_hook_raises_when_budget_exhausted(self):
        budget = _make_budget(max_retries=1)
        registry = HookRegistry()
        attach_budget_hooks(registry, budget)
        ctx = self._make_ctx()
        result = self._make_result()
        registry.fire_on_retry(result, ctx)  # consumes the single slot
        with pytest.raises(BudgetExceeded):
            registry.fire_on_retry(result, ctx)
