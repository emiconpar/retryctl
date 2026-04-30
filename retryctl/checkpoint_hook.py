"""Hooks that persist retry checkpoint state via HookRegistry."""
from __future__ import annotations

from retryctl.checkpoint import CheckpointState, CheckpointStore
from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult


def attach_checkpoint_hooks(registry: HookRegistry, store: CheckpointStore) -> None:
    """Register checkpoint hooks on *registry* using *store* for persistence."""
    registry.register_on_attempt_failure(_make_on_attempt_failure(store))
    registry.register_on_retry(_make_on_retry(store))
    registry.register_on_final_failure(_make_on_final_failure(store))
    registry.register_on_success(_make_on_success(store))


def _make_on_attempt_failure(store: CheckpointStore):
    def _on_attempt_failure(result: ExecutionResult, ctx: HookContext) -> None:
        state = CheckpointState(
            command=ctx.command,
            attempt=ctx.attempt,
            total_delay=ctx.total_delay,
            last_exit_code=result.exit_code,
        )
        store.save(state)
    return _on_attempt_failure


def _make_on_retry(store: CheckpointStore):
    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        if store.exists:
            state = store.load()
            if state is not None:
                state.attempt = ctx.attempt
                state.total_delay = ctx.total_delay
                store.save(state)
    return _on_retry


def _make_on_final_failure(store: CheckpointStore):
    def _on_final_failure(result: ExecutionResult, ctx: HookContext) -> None:
        store.clear()
    return _on_final_failure


def _make_on_success(store: CheckpointStore):
    def _on_success(result: ExecutionResult, ctx: HookContext) -> None:
        store.clear()
    return _on_success
