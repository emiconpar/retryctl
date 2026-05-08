"""Hooks that populate an EventLog from retry lifecycle callbacks."""
from __future__ import annotations

from retryctl.eventlog import EventLog, EventLogEntry
from retryctl.hooks import HookRegistry


def attach_eventlog_hooks(registry: HookRegistry, log: EventLog) -> None:
    """Register all lifecycle hooks that record events into *log*.

    Four hook types are attached:
    - ``attempt_failure``: recorded each time an attempt exits with a non-zero code.
    - ``retry``: recorded just before a retry delay begins.
    - ``final_failure``: recorded when all attempts are exhausted.
    - ``success``: recorded when an attempt exits successfully.
    """
    registry.register_on_attempt_failure(_make_on_attempt_failure(log))
    registry.register_on_retry(_make_on_retry(log))
    registry.register_on_final_failure(_make_on_final_failure(log))
    registry.register_on_success(_make_on_success(log))


def _make_on_attempt_failure(log: EventLog):
    def _on_attempt_failure(result, ctx) -> None:
        log.record(
            EventLogEntry(
                event_type="attempt_failure",
                attempt=ctx.attempt,
                exit_code=result.exit_code,
                message=f"Attempt {ctx.attempt} failed with exit code {result.exit_code}",
            )
        )

    return _on_attempt_failure


def _make_on_retry(log: EventLog):
    def _on_retry(result, ctx) -> None:
        log.record(
            EventLogEntry(
                event_type="retry",
                attempt=ctx.attempt,
                exit_code=result.exit_code,
                delay=ctx.last_delay,
                message=f"Retrying after {ctx.last_delay:.2f}s (attempt {ctx.attempt})",
            )
        )

    return _on_retry


def _make_on_final_failure(log: EventLog):
    def _on_final_failure(result, ctx) -> None:
        log.record(
            EventLogEntry(
                event_type="final_failure",
                attempt=ctx.attempt,
                exit_code=result.exit_code,
                message=f"All {ctx.attempt} attempt(s) exhausted",
            )
        )

    return _on_final_failure


def _make_on_success(log: EventLog):
    def _on_success(result, ctx) -> None:
        log.record(
            EventLogEntry(
                event_type="success",
                attempt=ctx.attempt,
                exit_code=result.exit_code,
                message=f"Succeeded on attempt {ctx.attempt}",
            )
        )

    return _on_success
