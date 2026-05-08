"""Hook integration for the cost guard."""
from __future__ import annotations

from retryctl.costguard import CostGuardConfig, CostGuardState, check_cost
from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult


def attach_costguard_hooks(
    registry: HookRegistry,
    config: CostGuardConfig,
    state: CostGuardState | None = None,
) -> CostGuardState:
    """Register cost-guard callbacks on *registry*.

    Returns the :class:`CostGuardState` instance being used so callers can
    inspect the accumulated cost after the run.
    """
    if state is None:
        state = CostGuardState()

    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        check_cost(
            state,
            config,
            attempt=ctx.attempt,
            delay=ctx.delay if ctx.delay is not None else 0.0,
        )

    registry.register_on_retry(_on_retry)
    return state
