"""Hook integration for RetryBudget."""
from __future__ import annotations

from retryctl.budget import RetryBudget
from retryctl.hooks import HookRegistry


def attach_budget_hooks(registry: HookRegistry, budget: RetryBudget) -> None:
    """Attach hooks so that every retry attempt is recorded against *budget*.

    If the budget is exhausted the ``on_retry`` hook raises :class:`BudgetExceeded`,
    which propagates up through the executor and aborts further retries.
    """
    registry.register_on_retry(_make_on_retry(budget))


def _make_on_retry(budget: RetryBudget):
    from retryctl.hooks import HookContext
    from retryctl.executor import ExecutionResult

    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:  # noqa: ARG001
        budget.check_and_record()

    return _on_retry
