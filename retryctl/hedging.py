"""Hedged retry support: fire a speculative second attempt after a delay."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class HedgingConfig:
    """Configuration for hedged requests."""

    delay: float
    """Seconds to wait before firing the speculative hedge attempt."""

    max_hedges: int = 1
    """Maximum number of additional hedge attempts to fire."""

    cancel_on_success: bool = True
    """If True, outstanding hedges are abandoned once any attempt succeeds."""

    def __post_init__(self) -> None:
        if self.delay <= 0:
            raise ValueError("delay must be positive")
        if self.max_hedges < 1:
            raise ValueError("max_hedges must be at least 1")


@dataclass
class HedgeRecord:
    """Tracks a single hedge attempt."""

    hedge_index: int
    fired_at: float
    succeeded: bool = False
    exit_code: int | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "hedge_index": self.hedge_index,
            "fired_at": self.fired_at,
            "succeeded": self.succeeded,
        }
        if self.exit_code is not None:
            d["exit_code"] = self.exit_code
        return d


@dataclass
class HedgeLog:
    """Accumulates hedge records for a single run."""

    records: List[HedgeRecord] = field(default_factory=list)

    def record(self, entry: HedgeRecord) -> None:
        self.records.append(entry)

    def any_succeeded(self) -> bool:
        return any(r.succeeded for r in self.records)

    def to_dict(self) -> dict:
        return {"hedges": [r.to_dict() for r in self.records]}
