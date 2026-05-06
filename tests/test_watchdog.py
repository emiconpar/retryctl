"""Tests for retryctl.watchdog."""
from __future__ import annotations

import time
import pytest

from retryctl.watchdog import Watchdog, WatchdogConfig, WatchdogTripped


# ---------------------------------------------------------------------------
# WatchdogConfig validation
# ---------------------------------------------------------------------------

class TestWatchdogConfig:
    def test_valid_config_accepted(self):
        cfg = WatchdogConfig(stall_timeout=5.0, key="mykey")
        assert cfg.stall_timeout == 5.0
        assert cfg.key == "mykey"

    def test_zero_stall_timeout_raises(self):
        with pytest.raises(ValueError, match="stall_timeout"):
            WatchdogConfig(stall_timeout=0)

    def test_negative_stall_timeout_raises(self):
        with pytest.raises(ValueError, match="stall_timeout"):
            WatchdogConfig(stall_timeout=-1.0)

    def test_blank_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            WatchdogConfig(stall_timeout=1.0, key="   ")

    def test_default_enabled_true(self):
        cfg = WatchdogConfig(stall_timeout=1.0)
        assert cfg.enabled is True


# ---------------------------------------------------------------------------
# Watchdog behaviour
# ---------------------------------------------------------------------------

def _make_watchdog(timeout: float = 0.1) -> tuple[Watchdog, list]:
    trips: list[tuple[str, float]] = []
    cfg = WatchdogConfig(stall_timeout=timeout, key="test")
    wd = Watchdog(config=cfg, on_trip=lambda k, t: trips.append((k, t)))
    return wd, trips


class TestWatchdogTrip:
    def test_trips_after_timeout(self):
        wd, trips = _make_watchdog(timeout=0.05)
        wd.start()
        time.sleep(0.12)
        assert wd.tripped is True
        assert len(trips) == 1
        assert trips[0] == ("test", 0.05)

    def test_does_not_trip_when_stopped_early(self):
        wd, trips = _make_watchdog(timeout=0.1)
        wd.start()
        wd.stop()
        time.sleep(0.15)
        assert wd.tripped is False
        assert trips == []

    def test_feed_resets_timer(self):
        wd, trips = _make_watchdog(timeout=0.08)
        wd.start()
        time.sleep(0.05)
        wd.feed()
        time.sleep(0.05)  # still within new window
        assert wd.tripped is False
        wd.stop()

    def test_tripped_false_initially(self):
        wd, _ = _make_watchdog()
        assert wd.tripped is False

    def test_restart_clears_tripped_flag(self):
        wd, trips = _make_watchdog(timeout=0.04)
        wd.start()
        time.sleep(0.08)
        assert wd.tripped is True
        wd.start()  # restart should reset
        assert wd.tripped is False
        wd.stop()


class TestWatchdogTrippedException:
    def test_exception_message_contains_key(self):
        exc = WatchdogTripped(key="myjob", stall_timeout=30.0)
        assert "myjob" in str(exc)

    def test_exception_message_contains_timeout(self):
        exc = WatchdogTripped(key="myjob", stall_timeout=30.0)
        assert "30.0" in str(exc)

    def test_attributes_set(self):
        exc = WatchdogTripped(key="k", stall_timeout=5.0)
        assert exc.key == "k"
        assert exc.stall_timeout == 5.0
