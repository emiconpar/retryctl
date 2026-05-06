"""Sampling support for retryctl — probabilistically suppress retries."""
from __future__ import annotations

import random
from dataclasses import dataclass, field


class SamplingSkipped(Exception):
    """Raised when a retry is suppressed by the sampler."""

    def __init__(self, rate: float) -> None:
        self.rate = rate
        super().__init__(f"retry suppressed by sampler (rate={rate!r})")


@dataclass
class SamplingConfig:
    """Configuration for probabilistic retry sampling.

    Attributes:
        rate: Probability [0.0, 1.0] that a retry is *allowed* to proceed.
              1.0 means always retry (no sampling); 0.0 means never retry.
        seed:  Optional RNG seed for deterministic testing.
    """

    rate: float
    seed: int | None = field(default=None)

    def __post_init__(self) -> None:
        if not (0.0 <= self.rate <= 1.0):
            raise ValueError(
                f"rate must be in [0.0, 1.0], got {self.rate!r}"
            )


class RetrySampler:
    """Decides probabilistically whether a retry should proceed."""

    def __init__(self, config: SamplingConfig) -> None:
        self._rate = config.rate
        self._rng = random.Random(config.seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_retry(self) -> bool:
        """Return True if the retry is allowed under the current rate."""
        return self._rng.random() < self._rate

    def check(self) -> None:
        """Raise SamplingSkipped if the retry should be suppressed."""
        if not self.should_retry():
            raise SamplingSkipped(self._rate)

    @property
    def rate(self) -> float:
        return self._rate
