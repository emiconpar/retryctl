"""Tests for the dead-letter queue module."""
from __future__ import annotations

import time
import pytest

from retryctl.deadletter import DeadLetterConfig, DeadLetterEntry, DeadLetterQueue


def _make_entry(**kwargs) -> DeadLetterEntry:
    defaults = dict(command=["echo", "hi"], exit_code=1, attempts=3)
    defaults.update(kwargs)
    return DeadLetterEntry(**defaults)


class TestDeadLetterConfig:
    def test_valid_config_accepted(self, tmp_path):
        cfg = DeadLetterConfig(path=str(tmp_path), max_entries=10)
        assert cfg.max_entries == 10

    def test_zero_max_entries_raises(self, tmp_path):
        with pytest.raises(ValueError, match="max_entries"):
            DeadLetterConfig(path=str(tmp_path), max_entries=0)


class TestDeadLetterEntry:
    def test_to_dict_round_trips(self):
        entry = _make_entry(reason="timeout")
        assert DeadLetterEntry.from_dict(entry.to_dict()) == entry

    def test_failed_at_is_recent(self):
        entry = _make_entry()
        assert abs(entry.failed_at - time.time()) < 2

    def test_labels_default_empty(self):
        entry = _make_entry()
        assert entry.labels == {}


class TestDeadLetterQueue:
    def test_push_and_retrieve(self, tmp_path):
        q = DeadLetterQueue(DeadLetterConfig(path=str(tmp_path)))
        q.push(_make_entry())
        entries = q.all()
        assert len(entries) == 1
        assert entries[0].command == ["echo", "hi"]

    def test_multiple_entries_ordered(self, tmp_path):
        q = DeadLetterQueue(DeadLetterConfig(path=str(tmp_path)))
        q.push(_make_entry(exit_code=1))
        q.push(_make_entry(exit_code=2))
        entries = q.all()
        assert [e.exit_code for e in entries] == [1, 2]

    def test_max_entries_enforced(self, tmp_path):
        q = DeadLetterQueue(DeadLetterConfig(path=str(tmp_path), max_entries=3))
        for i in range(5):
            q.push(_make_entry(exit_code=i))
        entries = q.all()
        assert len(entries) == 3
        assert entries[0].exit_code == 2  # oldest trimmed

    def test_clear_empties_queue(self, tmp_path):
        q = DeadLetterQueue(DeadLetterConfig(path=str(tmp_path)))
        q.push(_make_entry())
        q.clear()
        assert q.all() == []

    def test_empty_queue_returns_empty_list(self, tmp_path):
        q = DeadLetterQueue(DeadLetterConfig(path=str(tmp_path)))
        assert q.all() == []
