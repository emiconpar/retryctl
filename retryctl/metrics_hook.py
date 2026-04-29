"""Hook integration that populates RunMetrics during a retry run."""
from __future__ import annotations

from retryctl.hooks import HookContext, HookRegistry
from retryctl.metrics import RunMetrics
from retryctl.metrics_reporter import MetricsReporter, NullReporter


def attach_metrics_hooks(
    registry: HookRegistry,
    metrics: RunMetrics,
    reporter: MetricsReporter | None = None,
) -> None:
    """Register hooks on *registry* that record attempt data into *metrics*.

    Args:
        registry: The HookRegistry used by the executor.
        metrics: A RunMetrics instance to populate.
        reporter: Optional reporter called after the final outcome is recorded.
            Defaults to NullReporter (no output).
    """
    if reporter is None:
        reporter = NullReporter()

    def _on_attempt_failure(ctx: HookContext) -> None:
        metrics.record_attempt(
            attempt_number=ctx.attempt,
            exit_code=ctx.result.exit_code,
            duration=ctx.result.duration_seconds,
            delay_before_next=ctx.next_delay,
        )

    def _on_final_failure(ctx: HookContext) -> None:
        metrics.record_attempt(
            attempt_number=ctx.attempt,
            exit_code=ctx.result.exit_code,
            duration=ctx.result.duration_seconds,
        )
        metrics.finish(succeeded=False, final_exit_code=ctx.result.exit_code)
        reporter.report(metrics)

    def _on_success(ctx: HookContext) -> None:
        # Success is fired after the last (successful) attempt.
        metrics.record_attempt(
            attempt_number=ctx.attempt,
            exit_code=ctx.result.exit_code,
            duration=ctx.result.duration_seconds,
        )
        metrics.finish(succeeded=True, final_exit_code=ctx.result.exit_code)
        reporter.report(metrics)

    registry.register_on_attempt_failure(_on_attempt_failure)
    registry.register_on_final_failure(_on_final_failure)
    # Register success hook if the registry supports it
    if hasattr(registry, "register_on_success"):
        registry.register_on_success(_on_success)
