"""Hooks that integrate DryRunLog with the HookRegistry."""

from __future__ import annotations

from typing import List

from retryctl.dryrun import DryRunConfig, DryRunLog
from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult


def attach_dryrun_hooks(
    registry: HookRegistry,
    config: DryRunConfig,
    log: DryRunLog,
    command: List[str],
) -> None:
    """Attach dry-run recording hooks to *registry*."""
    if not config.enabled:
        return

    def _on_attempt_failure(result: ExecutionResult, ctx: HookContext) -> None:
        log.record(
            attempt=ctx.attempt_number,
            command=command,
            exit_code=config.simulated_exit_code,
        )
        if config.verbose:
            print(
                f"[dry-run] attempt {ctx.attempt_number} — "
                f"would have run: {' '.join(command)}"
            )

    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        if config.verbose:
            print(
                f"[dry-run] retry scheduled after attempt {ctx.attempt_number}"
            )

    def _on_final_failure(result: ExecutionResult, ctx: HookContext) -> None:
        log.record(
            attempt=ctx.attempt_number,
            command=command,
            exit_code=config.simulated_exit_code,
        )
        if config.verbose:
            print(f"[dry-run] final failure after {ctx.attempt_number} attempt(s)")
            print(log.summary())

    def _on_success(result: ExecutionResult, ctx: HookContext) -> None:
        log.record(
            attempt=ctx.attempt_number,
            command=command,
            exit_code=config.simulated_exit_code,
        )
        if config.verbose:
            print(
                f"[dry-run] success (simulated) on attempt {ctx.attempt_number}"
            )

    registry.register_on_attempt_failure(_on_attempt_failure)
    registry.register_on_retry(_on_retry)
    registry.register_on_final_failure(_on_final_failure)
    registry.register_on_success(_on_success)
