"""Tests for retryctl.circuitbreaker_hook."""
from __future__ import annotations

from unittest.mock import MagicMock, call
import pytest

from retryctl.circuitbreaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerTripped
from retryctl.circuitbreaker_hook import attach_circuitbreaker_hooks
from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult


def _make_result(exit_code: int = 1, succeeded: bool = False) -> ExecutionResult:
    return ExecutionResult(
        command=["echo", "hi"],
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        succeeded=succeeded,
    )


def _make_ctx() -> HookContext:
    return HookContext(attempt=1, max_attempts=3, command=["echo", "hi"])


def _make_breaker(**kwargs) -> CircuitBreaker:
    return CircuitBreaker(config=CircuitBreakerConfig(**kwargs))


class TestAttachCircuitBreakerHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.breaker = _make_breaker(failure_threshold=2)
        attach_circuitbreaker_hooks(self.registry, self.breaker)

    def test_attempt_failure_records_failure(self):
        result = _make_result()
        ctx = _make_ctx()
        self.registry.fire_on_attempt_failure(result, ctx)
        # One failure recorded — still closed but counter incremented
        assert self.breaker._consecutive_failures == 1

    def test_final_failure_records_failure(self):
        result = _make_result()
        ctx = _make_ctx()
        self.registry.fire_on_final_failure(result, ctx)
        assert self.breaker._consecutive_failures == 1

    def test_success_resets_breaker(self):
        self.breaker.record_failure()  # pre-seed a failure
        result = _make_result(exit_code=0, succeeded=True)
        ctx = _make_ctx()
        self.registry.fire_on_success(result, ctx)
        assert self.breaker._consecutive_failures == 0

    def test_retry_blocked_when_circuit_open(self):
        # Trip the breaker
        self.breaker.record_failure()
        self.breaker.record_failure()
        result = _make_result()
        ctx = _make_ctx()
        with pytest.raises(CircuitBreakerTripped):
            self.registry.fire_on_retry(result, ctx)

    def test_retry_allowed_when_circuit_closed(self):
        result = _make_result()
        ctx = _make_ctx()
        self.registry.fire_on_retry(result, ctx)  # should not raise
