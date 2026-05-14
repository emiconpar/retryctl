"""Hook integration for spillover: fires run_spillover on final failure."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult
from retryctl.spillover import SpilloverConfig, SpilloverResult, run_spillover


def attach_spillover_hooks(
    registry: HookRegistry,
    config: SpilloverConfig,
    on_spillover: Optional[Callable[[SpilloverResult], None]] = None,
) -> None:
    """Register a final-failure hook that runs the spillover command."""
    if not config.enabled:
        return

    def _on_final_failure(result: ExecutionResult, ctx: HookContext) -> None:
        spillover_result = run_spillover(config)
        if on_spillover is not None:
            on_spillover(spillover_result)

    registry.register_on_final_failure(_on_final_failure)
