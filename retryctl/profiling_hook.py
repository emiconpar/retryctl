"""Hook integration for run profiling."""
from __future__ import annotations

import time
from typing import Optional

from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult
from retryctl.profiling import ProfilingConfig, RunProfile


def attach_profiling_hooks(
    registry: HookRegistry,
    profile: RunProfile,
    config: Optional[ProfilingConfig] = None,
) -> None:
    """Register hooks that populate *profile* during a retry run."""
    cfg = config or ProfilingConfig()
    if not cfg.enabled:
        return

    profile.start_run()
    _state: dict = {}

    def _on_attempt_failure(result: ExecutionResult, ctx: HookContext) -> None:
        started = _state.pop(ctx.attempt, time.monotonic())
        profile.record_attempt(ctx.attempt, started, time.monotonic())

    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        _state[ctx.attempt + 1] = time.monotonic()

    def _on_final_failure(result: ExecutionResult, ctx: HookContext) -> None:
        started = _state.pop(ctx.attempt, time.monotonic())
        profile.record_attempt(ctx.attempt, started, time.monotonic())
        profile.finish_run()

    def _on_success(result: ExecutionResult, ctx: HookContext) -> None:
        started = _state.pop(ctx.attempt, time.monotonic())
        profile.record_attempt(ctx.attempt, started, time.monotonic())
        profile.finish_run()

    # Seed attempt 1 timing
    _state[1] = time.monotonic()

    registry.register_on_attempt_failure(_on_attempt_failure)
    registry.register_on_retry(_on_retry)
    registry.register_on_final_failure(_on_final_failure)
    registry.register_on_success(_on_success)
