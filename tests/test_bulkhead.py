"""Tests for retryctl.bulkhead."""
from __future__ import annotations

import threading
import pytest

from retryctl.bulkhead import (
    BulkheadConfig,
    BulkheadFull,
    BulkheadPartition,
    BulkheadRegistry,
)


class TestBulkheadConfig:
    def test_valid_config_accepted(self):
        cfg = BulkheadConfig(key="svc", max_concurrent=3)
        assert cfg.key == "svc"
        assert cfg.max_concurrent == 3

    def test_blank_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            BulkheadConfig(key="  ", max_concurrent=1)

    def test_zero_max_concurrent_raises(self):
        with pytest.raises(ValueError, match="max_concurrent"):
            BulkheadConfig(key="svc", max_concurrent=0)

    def test_negative_max_concurrent_raises(self):
        with pytest.raises(ValueError, match="max_concurrent"):
            BulkheadConfig(key="svc", max_concurrent=-1)

    def test_negative_queue_timeout_raises(self):
        with pytest.raises(ValueError, match="queue_timeout"):
            BulkheadConfig(key="svc", max_concurrent=1, queue_timeout=-0.1)

    def test_zero_queue_timeout_allowed(self):
        cfg = BulkheadConfig(key="svc", max_concurrent=1, queue_timeout=0.0)
        assert cfg.queue_timeout == 0.0

    def test_none_queue_timeout_allowed(self):
        cfg = BulkheadConfig(key="svc", max_concurrent=2, queue_timeout=None)
        assert cfg.queue_timeout is None


def _make_partition(limit: int = 2) -> BulkheadPartition:
    return BulkheadPartition(max_concurrent=limit)


class TestBulkheadPartition:
    def test_acquire_succeeds_within_limit(self):
        p = _make_partition(2)
        assert p.acquire(timeout=0) is True
        assert p.acquire(timeout=0) is True

    def test_acquire_fails_when_full(self):
        p = _make_partition(1)
        p.acquire(timeout=0)
        assert p.acquire(timeout=0) is False

    def test_active_count_tracks_acquisitions(self):
        p = _make_partition(3)
        assert p.active == 0
        p.acquire(timeout=0)
        assert p.active == 1
        p.acquire(timeout=0)
        assert p.active == 2

    def test_release_decrements_active(self):
        p = _make_partition(2)
        p.acquire(timeout=0)
        p.release()
        assert p.active == 0

    def test_release_allows_new_acquire(self):
        p = _make_partition(1)
        p.acquire(timeout=0)
        p.release()
        assert p.acquire(timeout=0) is True


class TestBulkheadRegistry:
    def setup_method(self):
        self.reg = BulkheadRegistry()

    def test_get_or_create_returns_partition(self):
        p = self.reg.get_or_create("svc", 3)
        assert isinstance(p, BulkheadPartition)

    def test_same_key_returns_same_partition(self):
        p1 = self.reg.get_or_create("svc", 3)
        p2 = self.reg.get_or_create("svc", 3)
        assert p1 is p2

    def test_active_count_zero_for_unknown_key(self):
        assert self.reg.active_count("unknown") == 0

    def test_active_count_reflects_partition(self):
        p = self.reg.get_or_create("svc", 2)
        p.acquire(timeout=0)
        assert self.reg.active_count("svc") == 1

    def test_reset_removes_partition(self):
        self.reg.get_or_create("svc", 2)
        self.reg.reset("svc")
        assert self.reg.active_count("svc") == 0


class TestBulkheadFull:
    def test_message_contains_key_and_limit(self):
        err = BulkheadFull(key="api", limit=5)
        assert "api" in str(err)
        assert "5" in str(err)
