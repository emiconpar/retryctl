"""Hook integration for load shedding."""
from __future__ import annotations

from retryctl.hooks import HookRegistry
from retryctl.shedding import SheddingState, LoadSheddingTripped


def attach_shedding_hooks(registry: HookRegistry, state: SheddingState) -> None:
    """Register hooks that enforce load shedding before each retry."""

    def _on_retry(result, ctx):
        _check(state, ctx)

    def _on_attempt_failure(result, ctx):
        _check(state, ctx)

    registry.register_on_retry(_on_retry)
    registry.register_on_attempt_failure(_on_attempt_failure)


def _check(state: SheddingState, ctx) -> None:
    """Perform the load check; propagate LoadSheddingTripped on overload."""
    try:
        state.check(ctx.attempt)
    except LoadSheddingTripped:
        raise
