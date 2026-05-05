"""Reporters for circuit breaker state."""
from __future__ import annotations

import json
import sys
from typing import IO

from retryctl.circuitbreaker import CircuitBreaker, CircuitState


class CircuitBreakerReporter:
    """Base class for circuit breaker state reporters."""

    def report(self, breaker: CircuitBreaker) -> None:
        raise NotImplementedError


class NullCircuitBreakerReporter(CircuitBreakerReporter):
    """No-op reporter used when circuit breaker reporting is disabled."""

    def report(self, breaker: CircuitBreaker) -> None:
        pass


class TextCircuitBreakerReporter(CircuitBreakerReporter):
    """Writes a human-readable circuit breaker summary to a stream."""

    def __init__(self, stream: IO[str] = sys.stderr) -> None:
        self._stream = stream

    def report(self, breaker: CircuitBreaker) -> None:
        state = breaker.state
        failures = breaker._consecutive_failures
        threshold = breaker.config.failure_threshold
        lines = [
            f"circuit_state={state.value}",
            f"consecutive_failures={failures}/{threshold}",
        ]
        if state == CircuitState.OPEN and breaker._opened_at is not None:
            import time
            elapsed = time.monotonic() - breaker._opened_at
            remaining = max(0.0, breaker.config.recovery_timeout - elapsed)
            lines.append(f"resets_in={remaining:.1f}s")
        self._stream.write(" ".join(lines) + "\n")


class JsonCircuitBreakerReporter(CircuitBreakerReporter):
    """Writes circuit breaker state as a JSON object to a stream."""

    def __init__(self, stream: IO[str] = sys.stderr) -> None:
        self._stream = stream

    def report(self, breaker: CircuitBreaker) -> None:
        import time
        state = breaker.state
        payload: dict = {
            "circuit_state": state.value,
            "consecutive_failures": breaker._consecutive_failures,
            "failure_threshold": breaker.config.failure_threshold,
            "recovery_timeout": breaker.config.recovery_timeout,
        }
        if state == CircuitState.OPEN and breaker._opened_at is not None:
            elapsed = time.monotonic() - breaker._opened_at
            payload["resets_in"] = round(max(0.0, breaker.config.recovery_timeout - elapsed), 3)
        self._stream.write(json.dumps(payload) + "\n")
