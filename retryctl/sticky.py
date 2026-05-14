"""Sticky retry: pin retries to a specific executor/node based on a key."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class StickyConfig:
    """Configuration for sticky retry behaviour."""

    key: str
    max_same_node_attempts: int = 3
    fallback_on_exhaust: bool = True

    def __post_init__(self) -> None:
        if not self.key or not self.key.strip():
            raise ValueError("key must be a non-blank string")
        if self.max_same_node_attempts < 1:
            raise ValueError("max_same_node_attempts must be >= 1")
        if not isinstance(self.fallback_on_exhaust, bool):
            raise TypeError("fallback_on_exhaust must be a bool")


@dataclass
class StickyState:
    """Runtime state tracking per-key attempt counts."""

    config: StickyConfig
    _counts: Dict[str, int] = field(default_factory=dict, init=False)
    _pinned: Dict[str, Optional[str]] = field(default_factory=dict, init=False)

    def pin(self, key: str, node: str) -> None:
        """Pin a key to a specific node."""
        self._pinned[key] = node
        self._counts[key] = 0

    def record_attempt(self, key: str) -> None:
        """Increment the attempt counter for a key."""
        self._counts[key] = self._counts.get(key, 0) + 1

    def should_fallback(self, key: str) -> bool:
        """Return True if the key has exhausted same-node attempts."""
        count = self._counts.get(key, 0)
        if count < self.config.max_same_node_attempts:
            return False
        return self.config.fallback_on_exhaust

    def get_pinned_node(self, key: str) -> Optional[str]:
        """Return the pinned node for a key, or None."""
        return self._pinned.get(key)

    def clear(self, key: str) -> None:
        """Clear pinning state for a key (e.g. after success)."""
        self._counts.pop(key, None)
        self._pinned.pop(key, None)

    def attempt_count(self, key: str) -> int:
        """Return the current attempt count for a key."""
        return self._counts.get(key, 0)
