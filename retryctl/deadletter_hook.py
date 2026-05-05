"""Hook integration for the dead-letter queue."""
from __future__ import annotations

from typing import Optional

from retryctl.deadletter import DeadLetterEntry, DeadLetterQueue
from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult


def attach_deadletter_hooks(
    registry: HookRegistry,
    queue: DeadLetterQueue,
    labels: Optional[dict] = None,
) -> None:
    """Register a hook that writes an entry to *queue* on final failure."""
    _labels = labels or {}

    def _on_final_failure(result: ExecutionResult, ctx: HookContext) -> None:
        entry = DeadLetterEntry(
            command=list(result.command),
            exit_code=result.exit_code,
            attempts=ctx.attempt,
            reason="final_failure",
            labels=dict(_labels),
        )
        queue.push(entry)

    registry.register_on_final_failure(_on_final_failure)
