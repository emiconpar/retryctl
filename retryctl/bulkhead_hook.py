"""Hook integration for the bulkhead pattern."""
from __future__ import annotations

from retryctl.bulkhead import BulkheadConfig, BulkheadFull, BulkheadRegistry
from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult

_registry = BulkheadRegistry()


def attach_bulkhead_hooks(
    hooks: HookRegistry,
    config: BulkheadConfig,
    registry: BulkheadRegistry | None = None,
) -> None:
    """Register bulkhead acquire/release around retry attempts."""
    _reg = registry if registry is not None else _registry
    partition = _reg.get_or_create(config.key, config.max_concurrent)

    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        acquired = partition.acquire(timeout=config.queue_timeout)
        if not acquired:
            raise BulkheadFull(config.key, config.max_concurrent)
        ctx.metadata["_bulkhead_acquired"] = True

    def _on_attempt_failure(result: ExecutionResult, ctx: HookContext) -> None:
        if ctx.metadata.pop("_bulkhead_acquired", False):
            partition.release()

    def _on_final_failure(result: ExecutionResult, ctx: HookContext) -> None:
        if ctx.metadata.pop("_bulkhead_acquired", False):
            partition.release()

    def _on_success(result: ExecutionResult, ctx: HookContext) -> None:
        if ctx.metadata.pop("_bulkhead_acquired", False):
            partition.release()

    hooks.register_on_retry(_on_retry)
    hooks.register_on_attempt_failure(_on_attempt_failure)
    hooks.register_on_final_failure(_on_final_failure)
    hooks.register_on_success(_on_success)
