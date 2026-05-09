"""Hooks that integrate HedgeLog with the HookRegistry."""
from __future__ import annotations

import time

from retryctl.hedging import HedgeLog, HedgeRecord, HedgingConfig
from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult


def attach_hedging_hooks(
    registry: HookRegistry,
    config: HedgingConfig,
    log: HedgeLog,
) -> None:
    """Register hedging hooks onto *registry*."""
    registry.register_on_retry(_make_on_retry(config, log))
    registry.register_on_success(_make_on_success(log))


def _make_on_retry(config: HedgingConfig, log: HedgeLog):
    hedge_count = 0

    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        nonlocal hedge_count
        if hedge_count >= config.max_hedges:
            return
        hedge_count += 1
        record = HedgeRecord(
            hedge_index=hedge_count,
            fired_at=time.monotonic(),
            succeeded=False,
            exit_code=result.exit_code,
        )
        log.record(record)

    return _on_retry


def _make_on_success(log: HedgeLog):
    def _on_success(result: ExecutionResult, ctx: HookContext) -> None:
        for record in log.records:
            if not record.succeeded:
                record.succeeded = config_cancel = True  # mark winning hedge
                break

    return _on_success
