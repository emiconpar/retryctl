"""Tests for retryctl.circuitbreaker."""
from __future__ import annotations

import time
import pytest

from retryctl.circuitbreaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerTripped,
    CircuitState,
)


def _make_breaker(**kwargs) -> CircuitBreaker:
    cfg = CircuitBreakerConfig(**kwargs)
    return CircuitBreaker(config=cfg)


class TestCircuitBreakerConfig:
    def test_valid_config_accepted(self):
        cfg = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=10.0)
        assert cfg.failure_threshold == 3

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            CircuitBreakerConfig(failure_threshold=0)

    def test_negative_recovery_timeout_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout"):
            CircuitBreakerConfig(recovery_timeout=-1.0)

    def test_zero_half_open_attempts_raises(self):
        with pytest.raises(ValueError, match="half_open_max_attempts"):
            CircuitBreakerConfig(half_open_max_attempts=0)


class TestCircuitBreakerClosed:
    def test_initial_state_is_closed(self):
        b = _make_breaker()
        assert b.state == CircuitState.CLOSED

    def test_allow_attempt_does_not_raise_when_closed(self):
        b = _make_breaker()
        b.allow_attempt()  # should not raise

    def test_failures_below_threshold_keep_closed(self):
        b = _make_breaker(failure_threshold=3)
        b.record_failure()
        b.record_failure()
        assert b.state == CircuitState.CLOSED

    def test_success_resets_failure_count(self):
        b = _make_breaker(failure_threshold=2)
        b.record_failure()
        b.record_success()
        b.record_failure()  # would open if count wasn't reset
        assert b.state == CircuitState.CLOSED


class TestCircuitBreakerOpen:
    def test_opens_after_threshold(self):
        b = _make_breaker(failure_threshold=2)
        b.record_failure()
        b.record_failure()
        assert b.state == CircuitState.OPEN

    def test_allow_attempt_raises_when_open(self):
        b = _make_breaker(failure_threshold=1)
        b.record_failure()
        with pytest.raises(CircuitBreakerTripped):
            b.allow_attempt()

    def test_tripped_exception_carries_state(self):
        b = _make_breaker(failure_threshold=1)
        b.record_failure()
        with pytest.raises(CircuitBreakerTripped) as exc_info:
            b.allow_attempt()
        assert exc_info.value.state == CircuitState.OPEN


class TestCircuitBreakerHalfOpen:
    def test_transitions_to_half_open_after_timeout(self):
        b = _make_breaker(failure_threshold=1, recovery_timeout=0.05)
        b.record_failure()
        time.sleep(0.06)
        assert b.state == CircuitState.HALF_OPEN

    def test_success_in_half_open_closes_circuit(self):
        b = _make_breaker(failure_threshold=1, recovery_timeout=0.05)
        b.record_failure()
        time.sleep(0.06)
        b.record_success()
        assert b.state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens_circuit(self):
        b = _make_breaker(failure_threshold=1, recovery_timeout=0.05)
        b.record_failure()
        time.sleep(0.06)
        b.record_failure()
        assert b.state == CircuitState.OPEN

    def test_exceeding_half_open_attempts_raises(self):
        b = _make_breaker(
            failure_threshold=1,
            recovery_timeout=0.05,
            half_open_max_attempts=1,
        )
        b.record_failure()
        time.sleep(0.06)
        b.allow_attempt()  # first probe allowed
        with pytest.raises(CircuitBreakerTripped):
            b.allow_attempt()  # second probe blocked
