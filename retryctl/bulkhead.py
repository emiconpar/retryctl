"""Bulkhead pattern: isolate retry pools by key to limit blast radius."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, Optional


class BulkheadFull(Exception):
    def __init__(self, key: str, limit: int) -> None:
        self.key = key
        self.limit = limit
        super().__init__(f"Bulkhead '{key}' is full (limit={limit})")


@dataclass
class BulkheadConfig:
    key: str
    max_concurrent: int
    queue_timeout: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.key or not self.key.strip():
            raise ValueError("key must not be blank")
        if self.max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive")
        if self.queue_timeout is not None and self.queue_timeout < 0:
            raise ValueError("queue_timeout must be non-negative")


class BulkheadPartition:
    """Semaphore-backed partition for a single bulkhead key."""

    def __init__(self, max_concurrent: int) -> None:
        self._semaphore = threading.Semaphore(max_concurrent)
        self._max = max_concurrent
        self._lock = threading.Lock()
        self._active = 0

    def acquire(self, timeout: Optional[float] = None) -> bool:
        acquired = self._semaphore.acquire(timeout=timeout if timeout is not None else -1)
        if acquired:
            with self._lock:
                self._active += 1
        return acquired

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
        self._semaphore.release()

    @property
    def active(self) -> int:
        with self._lock:
            return self._active


class BulkheadRegistry:
    """Global registry of named bulkhead partitions."""

    def __init__(self) -> None:
        self._partitions: Dict[str, BulkheadPartition] = {}
        self._lock = threading.Lock()

    def get_or_create(self, key: str, max_concurrent: int) -> BulkheadPartition:
        with self._lock:
            if key not in self._partitions:
                self._partitions[key] = BulkheadPartition(max_concurrent)
            return self._partitions[key]

    def active_count(self, key: str) -> int:
        with self._lock:
            partition = self._partitions.get(key)
            return partition.active if partition else 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._partitions.pop(key, None)
