"""Tests for retryctl.quota."""
from __future__ import annotations

import time
import pytest

from retryctl.quota import QuotaConfig, QuotaExceeded, RetryQuota


def _make_quota(max_retries: int = 3, window: float = 60.0, key: str = "test") -> RetryQuota:
    cfg = QuotaConfig(key=key, max_retries=max_retries, window_seconds=window)
    return RetryQuota(cfg)


# ---------------------------------------------------------------------------
# QuotaConfig validation
# ---------------------------------------------------------------------------

class TestQuotaConfig:
    def test_valid_config_accepted(self):
        cfg = QuotaConfig(key="svc", max_retries=5, window_seconds=30.0)
        assert cfg.max_retries == 5

    def test_blank_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            QuotaConfig(key="  ", max_retries=3, window_seconds=10.0)

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            QuotaConfig(key="", max_retries=3, window_seconds=10.0)

    def test_zero_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries"):
            QuotaConfig(key="k", max_retries=0, window_seconds=10.0)

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries"):
            QuotaConfig(key="k", max_retries=-1, window_seconds=10.0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            QuotaConfig(key="k", max_retries=3, window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            QuotaConfig(key="k", max_retries=3, window_seconds=-5.0)


# ---------------------------------------------------------------------------
# RetryQuota behaviour
# ---------------------------------------------------------------------------

class TestRetryQuota:
    def test_allows_up_to_limit(self):
        quota = _make_quota(max_retries=3)
        for _ in range(3):
            quota.check_and_record()  # should not raise

    def test_raises_on_exceeding_limit(self):
        quota = _make_quota(max_retries=2)
        quota.check_and_record()
        quota.check_and_record()
        with pytest.raises(QuotaExceeded):
            quota.check_and_record()

    def test_quota_exceeded_carries_metadata(self):
        quota = _make_quota(max_retries=1, key="mykey")
        quota.check_and_record()
        with pytest.raises(QuotaExceeded) as exc_info:
            quota.check_and_record()
        err = exc_info.value
        assert err.key == "mykey"
        assert err.used == 1
        assert err.limit == 1

    def test_current_usage_starts_at_zero(self):
        quota = _make_quota()
        assert quota.current_usage() == 0

    def test_current_usage_tracks_records(self):
        quota = _make_quota(max_retries=5)
        quota.check_and_record()
        quota.check_and_record()
        assert quota.current_usage() == 2

    def test_old_entries_expire(self):
        quota = _make_quota(max_retries=2, window=0.05)
        quota.check_and_record()
        quota.check_and_record()
        time.sleep(0.1)
        # Window has passed; should allow new entries
        quota.check_and_record()  # should not raise
        assert quota.current_usage() == 1
