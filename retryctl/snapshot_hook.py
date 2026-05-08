"""Hooks that populate a RunSnapshot during a retry run."""
from __future__ import annotations

from retryctl.executor import ExecutionResult
from retryctl.hooks import HookContext, HookRegistry
from retryctl.snapshot import RunSnapshot, SnapshotEntry


def attach_snapshot_hooks(
    registry: HookRegistry,
    snapshot: RunSnapshot,
) -> None:
    """Register hooks that record each attempt into *snapshot*."""

    def _on_attempt_failure(result: ExecutionResult, ctx: HookContext) -> None:
        entry = SnapshotEntry(
            attempt=ctx.attempt_number,
            exit_code=result.exit_code,
            succeeded=False,
            delay_after=0.0,
        )
        snapshot.record(entry)

    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        # Update the delay on the last recorded entry for this attempt.
        if snapshot.entries:
            last = snapshot.entries[-1]
            if last.attempt == ctx.attempt_number:
                last.delay_after = ctx.next_delay

    def _on_final_failure(result: ExecutionResult, ctx: HookContext) -> None:
        snapshot.final_succeeded = False

    def _on_success(result: ExecutionResult, ctx: HookContext) -> None:
        entry = SnapshotEntry(
            attempt=ctx.attempt_number,
            exit_code=result.exit_code,
            succeeded=True,
            delay_after=0.0,
        )
        snapshot.record(entry)
        snapshot.final_succeeded = True

    registry.register_on_attempt_failure(_on_attempt_failure)
    registry.register_on_retry(_on_retry)
    registry.register_on_final_failure(_on_final_failure)
    registry.register_on_success(_on_success)
