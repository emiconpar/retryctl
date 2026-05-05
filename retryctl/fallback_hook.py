"""Hook integration for fallback command execution on final failure."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.fallback import FallbackConfig, FallbackResult, run_fallback
from retryctl.hooks import HookContext, HookRegistry


def attach_fallback_hooks(
    registry: HookRegistry,
    config: FallbackConfig,
    on_fallback: Optional[Callable[[FallbackResult], None]] = None,
) -> None:
    """Register a final-failure hook that runs the fallback command.

    Args:
        registry: The hook registry to attach to.
        config: Fallback command configuration.
        on_fallback: Optional callback invoked with the fallback result.
    """

    def _on_final_failure(ctx: HookContext) -> None:
        result = run_fallback(config)
        if on_fallback is not None:
            on_fallback(result)

    registry.register_on_final_failure(_on_final_failure)
