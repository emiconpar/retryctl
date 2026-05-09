"""Tests for retryctl.hedging_hook."""
from __future__ import annotations

from unittest.mock import MagicMock

from retryctl.hedging import HedgeLog, HedgingConfig
from retryctl.hedging_hook import attach_hedging_hooks
from retryctl.hooks import HookRegistry
from retryctl.executor import ExecutionResult


def _make_result(exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        succeeded=exit_code == 0,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
    )


def _make_ctx() -> MagicMock:
    return MagicMock()


class TestAttachHedgingHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.config = HedgingConfig(delay=0.1, max_hedges=2)
        self.log = HedgeLog()
        attach_hedging_hooks(self.registry, self.config, self.log)

    def _fire_retry(self, exit_code: int = 1) -> None:
        result = _make_result(exit_code=exit_code)
        ctx = _make_ctx()
        for fn in self.registry._on_retry:
            fn(result, ctx)

    def test_hedge_recorded_on_retry(self):
        self._fire_retry()
        assert len(self.log.records) == 1

    def test_hedge_index_increments(self):
        self._fire_retry()
        self._fire_retry()
        assert self.log.records[0].hedge_index == 1
        assert self.log.records[1].hedge_index == 2

    def test_max_hedges_respected(self):
        for _ in range(5):
            self._fire_retry()
        assert len(self.log.records) == 2

    def test_exit_code_stored_in_record(self):
        self._fire_retry(exit_code=42)
        assert self.log.records[0].exit_code == 42

    def test_initial_succeeded_is_false(self):
        self._fire_retry()
        assert self.log.records[0].succeeded is False

    def test_hooks_registered(self):
        assert len(self.registry._on_retry) >= 1
        assert len(self.registry._on_success) >= 1
