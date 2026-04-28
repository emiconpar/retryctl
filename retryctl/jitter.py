"""Jitter strategies for backoff delays in retryctl."""
from __future__ import annotations

import random
from enum import Enum
from typing import Callable


class JitterStrategy(str, Enum):
    """Available jitter strategies."""

    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


# Type alias for a jitter function: (base_delay, previous_delay) -> jittered_delay
JitterFn = Callable[[float, float], float]


def _no_jitter(delay: float, _prev: float) -> float:
    return delay


def _full_jitter(delay: float, _prev: float) -> float:
    """Uniform random value between 0 and *delay*."""
    return random.uniform(0, delay)


def _equal_jitter(delay: float, _prev: float) -> float:
    """Half fixed, half random — balances predictability and spread."""
    half = delay / 2.0
    return half + random.uniform(0, half)


def _decorrelated_jitter(delay: float, prev: float) -> float:
    """Decorrelated jitter: random between *delay* and 3× previous delay."""
    return random.uniform(delay, max(delay, prev * 3))


_STRATEGY_MAP: dict[JitterStrategy, JitterFn] = {
    JitterStrategy.NONE: _no_jitter,
    JitterStrategy.FULL: _full_jitter,
    JitterStrategy.EQUAL: _equal_jitter,
    JitterStrategy.DECORRELATED: _decorrelated_jitter,
}


def get_jitter_fn(strategy: JitterStrategy) -> JitterFn:
    """Return the jitter function for *strategy*."""
    try:
        return _STRATEGY_MAP[strategy]
    except KeyError:  # pragma: no cover
        raise ValueError(f"Unknown jitter strategy: {strategy!r}")


def apply_jitter(
    delay: float,
    prev_delay: float,
    strategy: JitterStrategy = JitterStrategy.NONE,
) -> float:
    """Apply *strategy* jitter to *delay* and return the result."""
    fn = get_jitter_fn(strategy)
    return fn(delay, prev_delay)
