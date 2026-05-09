"""Quota enforcement: cap the total number of retries across a shared key."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict


class QuotaExceeded(Exception):
    def __init__(self, key: str, used: int, limit: int) -> None:
        self.key = key
        self.used = used
        self.limit = limit
        super().__init__(
            f"Retry quota exceeded for '{key}': used {used}/{limit}"
        )


@dataclass
class QuotaConfig:
    key: str
    max_retries: int
    window_seconds: float

    def __post_init__(self) -> None:
        if not self.key or not self.key.strip():
            raise ValueError("key must not be blank")
        if self.max_retries <= 0:
            raise ValueError("max_retries must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class _QuotaBucket:
    timestamps: list = field(default_factory=list)


class RetryQuota:
    """Sliding-window retry quota shared across callers using the same key."""

    def __init__(self, config: QuotaConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._buckets: Dict[str, _QuotaBucket] = {}

    def _bucket(self, key: str) -> _QuotaBucket:
        if key not in self._buckets:
            self._buckets[key] = _QuotaBucket()
        return self._buckets[key]

    def _prune(self, bucket: _QuotaBucket, now: float) -> None:
        cutoff = now - self._config.window_seconds
        bucket.timestamps = [t for t in bucket.timestamps if t >= cutoff]

    def check_and_record(self) -> None:
        """Record a retry attempt; raise QuotaExceeded if the limit is hit."""
        now = time.monotonic()
        with self._lock:
            bucket = self._bucket(self._config.key)
            self._prune(bucket, now)
            used = len(bucket.timestamps)
            if used >= self._config.max_retries:
                raise QuotaExceeded(self._config.key, used, self._config.max_retries)
            bucket.timestamps.append(now)

    def current_usage(self) -> int:
        now = time.monotonic()
        with self._lock:
            bucket = self._bucket(self._config.key)
            self._prune(bucket, now)
            return len(bucket.timestamps)
