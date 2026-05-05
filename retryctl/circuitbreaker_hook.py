"""Hooks that integrate the circuit breaker with the retry lifecycle."""
from __future__ import annotations

from retryctl.circuitbreaker import CircuitBreaker
from retryctl.hooks import HookRegistry
from retryctl.hooks import HookContext
from retryctl.executor import ExecutionResult


def attach_circuitbreaker_hooks(
    registry: HookRegistry,
    breaker: CircuitBreaker,
) -> None:
    """Register circuit-breaker callbacks on *registry*."""
    registry.register_on_attempt_failure(_make_on_attempt_failure(breaker))
    registry.register_on_retry(_make_on_retry(breaker))
    registry.register_on_final_failure(_make_on_final_failure(breaker))
    registry.register_on_success(_make_on_success(breaker))


def _make_on_attempt_failure(breaker: CircuitBreaker):
    def _on_attempt_failure(result: ExecutionResult, ctx: HookContext) -> None:
        breaker.record_failure()

    return _on_attempt_failure


def _make_on_retry(breaker: CircuitBreaker):
    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        # Raises CircuitBreakerTripped if circuit is open
        breaker.allow_attempt()

    return _on_retry


def _make_on_final_failure(breaker: CircuitBreaker):
    def _on_final_failure(result: ExecutionResult, ctx: HookContext) -> None:
        breaker.record_failure()

    return _on_final_failure


def _make_on_success(breaker: CircuitBreaker):
    def _on_success(result: ExecutionResult, ctx: HookContext) -> None:
        breaker.record_success()

    return _on_success
