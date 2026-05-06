"""Hook attachment for correlation ID injection into retry lifecycle."""
from __future__ import annotations

from retryctl.correlation import CorrelationContext
from retryctl.hooks import HookContext, HookRegistry


def attach_correlation_hooks(
    registry: HookRegistry,
    ctx: CorrelationContext,
) -> None:
    """Register hooks that stamp the correlation ID onto every HookContext."""

    def _inject(hook_ctx: HookContext) -> None:
        hook_ctx.metadata["correlation_id"] = ctx.correlation_id

    registry.register_on_attempt_failure(_inject)
    registry.register_on_retry(_inject)
    registry.register_on_final_failure(_inject)
    registry.register_on_success(_inject)
