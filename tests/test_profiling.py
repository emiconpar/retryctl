"""Tests for retryctl.profiling."""
from __future__ import annotations

import time
import pytest

from retryctl.profiling import AttemptTiming, ProfilingConfig, RunProfile


# ---------------------------------------------------------------------------
# ProfilingConfig
# ---------------------------------------------------------------------------

class TestProfilingConfig:
    def test_valid_config_accepted(self):
        cfg = ProfilingConfig(enabled=True, include_per_attempt=False)
        assert cfg.enabled is True
        assert cfg.include_per_attempt is False

    def test_non_bool_enabled_raises(self):
        with pytest.raises(TypeError):
            ProfilingConfig(enabled="yes")  # type: ignore

    def test_non_bool_include_per_attempt_raises(self):
        with pytest.raises(TypeError):
            ProfilingConfig(include_per_attempt=1)  # type: ignore


# ---------------------------------------------------------------------------
# AttemptTiming
# ---------------------------------------------------------------------------

class TestAttemptTiming:
    def test_duration_computed(self):
        t = AttemptTiming(attempt=1, started_at=0.0, ended_at=1.5)
        assert t.duration == pytest.approx(1.5)

    def test_to_dict_round_trips(self):
        t = AttemptTiming(attempt=2, started_at=1.0, ended_at=2.0)
        d = t.to_dict()
        assert d["attempt"] == 2
        assert d["duration_s"] == pytest.approx(1.0)
        assert "started_at" in d
        assert "ended_at" in d


# ---------------------------------------------------------------------------
# RunProfile
# ---------------------------------------------------------------------------

def _make_profile() -> RunProfile:
    p = RunProfile()
    p.start_run()
    return p


class TestRunProfile:
    def test_no_timings_initially(self):
        p = RunProfile()
        assert p.attempt_timings == []

    def test_record_attempt_stores_entry(self):
        p = _make_profile()
        now = time.monotonic()
        p.record_attempt(1, now, now + 0.1)
        assert len(p.attempt_timings) == 1

    def test_total_duration_none_before_finish(self):
        p = _make_profile()
        assert p.total_duration is None

    def test_total_duration_after_finish(self):
        p = _make_profile()
        time.sleep(0.01)
        p.finish_run()
        assert p.total_duration is not None
        assert p.total_duration > 0

    def test_average_attempt_duration_none_when_empty(self):
        p = RunProfile()
        assert p.average_attempt_duration is None

    def test_average_attempt_duration_computed(self):
        p = _make_profile()
        p.record_attempt(1, 0.0, 1.0)
        p.record_attempt(2, 1.0, 3.0)
        assert p.average_attempt_duration == pytest.approx(1.5)

    def test_to_dict_includes_per_attempt(self):
        p = _make_profile()
        p.record_attempt(1, 0.0, 0.5)
        p.finish_run()
        d = p.to_dict(include_per_attempt=True)
        assert "attempts" in d
        assert len(d["attempts"]) == 1

    def test_to_dict_excludes_per_attempt_when_false(self):
        p = _make_profile()
        p.record_attempt(1, 0.0, 0.5)
        p.finish_run()
        d = p.to_dict(include_per_attempt=False)
        assert "attempts" not in d
