"""Tests for retryctl.metrics."""
from __future__ import annotations

import time

import pytest

from retryctl.metrics import AttemptRecord, RunMetrics


def _make_metrics(command: list[str] | None = None) -> RunMetrics:
    return RunMetrics(command=command or ["echo", "hello"])


class TestAttemptRecord:
    def test_stores_fields(self):
        rec = AttemptRecord(attempt_number=1, exit_code=0, duration_seconds=0.5)
        assert rec.attempt_number == 1
        assert rec.exit_code == 0
        assert rec.duration_seconds == 0.5
        assert rec.delay_before_next is None

    def test_optional_delay(self):
        rec = AttemptRecord(attempt_number=2, exit_code=1, duration_seconds=0.1, delay_before_next=2.0)
        assert rec.delay_before_next == 2.0


class TestRunMetrics:
    def test_initial_state(self):
        m = _make_metrics()
        assert m.total_attempts == 0
        assert m.total_delay_seconds == 0.0
        assert not m.succeeded

    def test_record_attempt_increments_count(self):
        m = _make_metrics()
        m.record_attempt(1, exit_code=1, duration=0.2, delay_before_next=1.0)
        m.record_attempt(2, exit_code=0, duration=0.1)
        assert m.total_attempts == 2

    def test_total_delay_sums_delays(self):
        m = _make_metrics()
        m.record_attempt(1, exit_code=1, duration=0.1, delay_before_next=1.5)
        m.record_attempt(2, exit_code=1, duration=0.1, delay_before_next=3.0)
        m.record_attempt(3, exit_code=0, duration=0.1)
        assert m.total_delay_seconds == pytest.approx(4.5)

    def test_finish_sets_succeeded(self):
        m = _make_metrics()
        m.record_attempt(1, exit_code=0, duration=0.05)
        m.finish(succeeded=True, final_exit_code=0)
        assert m.succeeded is True
        assert m.final_exit_code == 0

    def test_finish_records_duration(self):
        m = _make_metrics()
        time.sleep(0.01)
        m.finish(succeeded=False, final_exit_code=1)
        assert m.total_duration_seconds >= 0.01

    def test_to_dict_structure(self):
        m = _make_metrics(["ls", "-la"])
        m.record_attempt(1, exit_code=2, duration=0.3, delay_before_next=1.0)
        m.finish(succeeded=False, final_exit_code=2)
        d = m.to_dict()
        assert d["command"] == ["ls", "-la"]
        assert d["succeeded"] is False
        assert d["total_attempts"] == 1
        assert len(d["attempts"]) == 1
        assert d["attempts"][0]["attempt_number"] == 1
        assert d["attempts"][0]["delay_before_next"] == 1.0
