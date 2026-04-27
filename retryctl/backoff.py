"""Backoff strategy implementations for retryctl."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BackoffStrategy(str, Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class BackoffConfig:
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: bool = False
    jitter_range: float = 0.5
    _attempt: int = field(default=0, init=False, repr=False)

    def reset(self) -> None:
        """Reset attempt counter."""
        self._attempt = 0

    def next_delay(self) -> float:
        """Calculate the next delay based on the configured strategy."""
        delay = self._compute_delay(self._attempt)
        self._attempt += 1
        return delay

    def _compute_delay(self, attempt: int) -> float:
        strategy = self.strategy

        if strategy == BackoffStrategy.FIXED:
            delay = self.base_delay

        elif strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay * (attempt + 1)

        elif strategy in (BackoffStrategy.EXPONENTIAL, BackoffStrategy.EXPONENTIAL_JITTER):
            delay = self.base_delay * (self.multiplier ** attempt)
            if strategy == BackoffStrategy.EXPONENTIAL_JITTER or self.jitter:
                jitter_offset = random.uniform(-self.jitter_range, self.jitter_range) * delay
                delay += jitter_offset

        else:
            delay = self.base_delay

        return max(0.0, min(delay, self.max_delay))


def create_backoff(strategy: str, base_delay: float = 1.0, max_delay: float = 60.0,
                   multiplier: float = 2.0, jitter: bool = False) -> BackoffConfig:
    """Factory function to create a BackoffConfig from string strategy name."""
    try:
        strat_enum = BackoffStrategy(strategy)
    except ValueError:
        valid = [s.value for s in BackoffStrategy]
        raise ValueError(f"Unknown strategy '{strategy}'. Valid options: {valid}")

    return BackoffConfig(
        strategy=strat_enum,
        base_delay=base_delay,
        max_delay=max_delay,
        multiplier=multiplier,
        jitter=jitter,
    )
