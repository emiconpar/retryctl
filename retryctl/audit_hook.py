"""Hooks that populate an AuditLog during a retry run."""
from __future__ import annotations

from retryctl.audit import AuditLog, make_audit_event
from retryctl.hooks import HookRegistry
from retryctl.hooks import HookContext
from retryctl.executor import ExecutionResult


def attach_audit_hooks(registry: HookRegistry, audit_log: AuditLog) -> None:
    """Register hooks that append events to *audit_log*."""

    def _on_attempt_failure(result: ExecutionResult, ctx: HookContext) -> None:
        event = make_audit_event(
            attempt=ctx.attempt_number,
            exit_code=result.exit_code,
            succeeded=False,
            note="attempt_failure",
        )
        audit_log.record(event)

    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        event = make_audit_event(
            attempt=ctx.attempt_number,
            exit_code=result.exit_code,
            succeeded=False,
            delay_before_next=ctx.next_delay,
            note="retry_scheduled",
        )
        audit_log.record(event)

    def _on_final_failure(result: ExecutionResult, ctx: HookContext) -> None:
        event = make_audit_event(
            attempt=ctx.attempt_number,
            exit_code=result.exit_code,
            succeeded=False,
            note="final_failure",
        )
        audit_log.record(event)

    def _on_success(result: ExecutionResult, ctx: HookContext) -> None:
        event = make_audit_event(
            attempt=ctx.attempt_number,
            exit_code=result.exit_code,
            succeeded=True,
            note="success",
        )
        audit_log.record(event)

    registry.register_on_attempt_failure(_on_attempt_failure)
    registry.register_on_retry(_on_retry)
    registry.register_on_final_failure(_on_final_failure)
    registry.register_on_success(_on_success)
