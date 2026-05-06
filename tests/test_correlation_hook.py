"""Tests for retryctl.correlation_hook."""
from __future__ import annotations

from unittest.mock import MagicMock

from retryctl.correlation import CorrelationConfig, CorrelationContext
from retryctl.correlation_hook import attach_correlation_hooks
from retryctl.executor import ExecutionResult
from retryctl.hooks import HookContext, HookRegistry


def _make_result() -> ExecutionResult:
    return ExecutionResult(
        succeeded=False,
        exit_code=1,
        stdout="",
        stderr="",
        attempts=1,
        total_delay=0.0,
    )


def _make_ctx() -> HookContext:
    return HookContext(
        attempt=1,
        result=_make_result(),
        metadata={},
    )


class TestAttachCorrelationHooks:
    def setup_method(self) -> None:
        self.registry = HookRegistry()
        self.corr_ctx = CorrelationContext.generate(
            CorrelationConfig(prefix="t-")
        )
        attach_correlation_hooks(self.registry, self.corr_ctx)

    def _fire_all(self, hook_ctx: HookContext) -> None:
        for fn in self.registry._on_attempt_failure:
            fn(hook_ctx)
        for fn in self.registry._on_retry:
            fn(hook_ctx)
        for fn in self.registry._on_final_failure:
            fn(hook_ctx)
        for fn in self.registry._on_success:
            fn(hook_ctx)

    def test_correlation_id_injected_on_attempt_failure(self) -> None:
        hctx = _make_ctx()
        for fn in self.registry._on_attempt_failure:
            fn(hctx)
        assert hctx.metadata["correlation_id"] == self.corr_ctx.correlation_id

    def test_correlation_id_injected_on_retry(self) -> None:
        hctx = _make_ctx()
        for fn in self.registry._on_retry:
            fn(hctx)
        assert hctx.metadata["correlation_id"] == self.corr_ctx.correlation_id

    def test_correlation_id_injected_on_final_failure(self) -> None:
        hctx = _make_ctx()
        for fn in self.registry._on_final_failure:
            fn(hctx)
        assert hctx.metadata["correlation_id"] == self.corr_ctx.correlation_id

    def test_correlation_id_injected_on_success(self) -> None:
        hctx = _make_ctx()
        for fn in self.registry._on_success:
            fn(hctx)
        assert hctx.metadata["correlation_id"] == self.corr_ctx.correlation_id

    def test_all_four_hooks_registered(self) -> None:
        assert len(self.registry._on_attempt_failure) >= 1
        assert len(self.registry._on_retry) >= 1
        assert len(self.registry._on_final_failure) >= 1
        assert len(self.registry._on_success) >= 1
