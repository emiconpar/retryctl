"""Tests for retryctl.snapshot."""
import time

import pytest

from retryctl.snapshot import RunSnapshot, SnapshotEntry


def _make_entry(
    attempt: int = 1,
    exit_code: int = 1,
    succeeded: bool = False,
    delay_after: float = 0.5,
) -> SnapshotEntry:
    return SnapshotEntry(
        attempt=attempt,
        exit_code=exit_code,
        succeeded=succeeded,
        delay_after=delay_after,
    )


class TestSnapshotEntry:
    def test_to_dict_round_trips(self):
        entry = _make_entry(attempt=2, exit_code=42, succeeded=False, delay_after=1.5)
        d = entry.to_dict()
        restored = SnapshotEntry.from_dict(d)
        assert restored.attempt == 2
        assert restored.exit_code == 42
        assert restored.succeeded is False
        assert restored.delay_after == 1.5

    def test_optional_exit_code_none(self):
        entry = SnapshotEntry(attempt=1, exit_code=None, succeeded=False, delay_after=0.0)
        d = entry.to_dict()
        assert d["exit_code"] is None
        restored = SnapshotEntry.from_dict(d)
        assert restored.exit_code is None

    def test_timestamp_is_recent(self):
        before = time.time()
        entry = _make_entry()
        after = time.time()
        assert before <= entry.timestamp <= after


class TestRunSnapshot:
    def test_record_appends_entry(self):
        snap = RunSnapshot(command=["echo", "hi"])
        snap.record(_make_entry(attempt=1))
        assert snap.total_attempts() == 1

    def test_total_delay_sums_entries(self):
        snap = RunSnapshot(command=["ls"])
        snap.record(_make_entry(delay_after=1.0))
        snap.record(_make_entry(delay_after=2.5))
        assert snap.total_delay() == pytest.approx(3.5)

    def test_to_dict_round_trips(self):
        snap = RunSnapshot(command=["false"])
        snap.record(_make_entry(attempt=1, delay_after=0.25))
        snap.final_succeeded = False
        d = snap.to_dict()
        restored = RunSnapshot.from_dict(d)
        assert restored.command == ["false"]
        assert restored.final_succeeded is False
        assert len(restored.entries) == 1
        assert restored.entries[0].delay_after == pytest.approx(0.25)

    def test_empty_snapshot_total_attempts_zero(self):
        snap = RunSnapshot(command=["true"])
        assert snap.total_attempts() == 0
        assert snap.total_delay() == 0.0
