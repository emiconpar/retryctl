"""Cost guard: abort retries once a cumulative cost threshold is exceeded."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


class CostGuardExceeded(Exception):
    """Raised when the cumulative retry cost exceeds the configured budget."""

    def __init__(self, total: float, limit: float) -> None:
        self.total = total
        self.limit = limit
        super().__init__(
            f"Retry cost budget exceeded: accumulated {total:.4f}, limit {limit:.4f}"
        )


@dataclass
class CostGuardConfig:
    """Configuration for the cost guard."""

    max_cost: float
    cost_fn: Callable[[int, float], float] = field(
        default=lambda attempt, delay: delay
    )

    def __post_init__(self) -> None:
        if self.max_cost <= 0:
            raise ValueError("max_cost must be positive")


@dataclass
class CostGuardState:
    """Mutable state tracking accumulated cost for a single run."""

    _total: float = field(default=0.0, init=False)

    @property
    def total(self) -> float:
        return self._total

    def add(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("cost amount must be non-negative")
        self._total += amount

    def reset(self) -> None:
        self._total = 0.0


def check_cost(
    state: CostGuardState,
    config: CostGuardConfig,
    attempt: int,
    delay: float,
) -> None:
    """Accumulate cost for *attempt* + *delay* and raise if over budget.

    Parameters
    ----------
    state:   per-run mutable state
    config:  static configuration
    attempt: 1-based attempt number that just failed
    delay:   seconds we are about to sleep before the next attempt
    """
    cost = config.cost_fn(attempt, delay)
    state.add(cost)
    if state.total > config.max_cost:
        raise CostGuardExceeded(state.total, config.max_cost)
