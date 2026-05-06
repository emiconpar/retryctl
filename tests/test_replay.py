"""Tests for retryctl.replay."""
from __future__ import annotations

import json
import pytest

from retryctl.replay import ReplayConfig, ReplayEntry, ReplayQueue


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_entry(**kwargs) -> ReplayEntry:
    defaults = dict(command=["echo", "hi"], exit_code=1, attempts=3)
    defaults.update(kwargs)
    return ReplayEntry(**defaults)


# ---------------------------------------------------------------------------
# ReplayConfig
# ---------------------------------------------------------------------------

class TestReplayConfig:
    def test_valid_config_accepted(self):
        cfg = ReplayConfig(path="/tmp/replay.jsonl", max_entries=50)
        assert cfg.max_entries == 50

    def test_zero_max_entries_raises(self):
        with pytest.raises(ValueError, match="max_entries"):
            ReplayConfig(path="/tmp/r.jsonl", max_entries=0)

    def test_negative_max_entries_raises(self):
        with pytest.raises(ValueError, match="max_entries"):
            ReplayConfig(path="/tmp/r.jsonl", max_entries=-1)

    def test_empty_path_raises(self):
        with pytest.raises(ValueError, match="path"):
            ReplayConfig(path="", max_entries=10)

    def test_blank_path_raises(self):
        with pytest.raises(ValueError, match="path"):
            ReplayConfig(path="   ", max_entries=10)


# ---------------------------------------------------------------------------
# ReplayEntry
# ---------------------------------------------------------------------------

class TestReplayEntry:
    def test_to_dict_round_trips(self):
        entry = _make_entry(correlation_id="abc", labels={"env": "prod"})
        d = entry.to_dict()
        restored = ReplayEntry.from_dict(d)
        assert restored.command == entry.command
        assert restored.exit_code == entry.exit_code
        assert restored.correlation_id == "abc"
        assert restored.labels == {"env": "prod"}

    def test_to_dict_omits_none_fields(self):
        entry = _make_entry()
        d = entry.to_dict()
        assert "correlation_id" not in d
        assert "labels" not in d

    def test_created_at_is_recent(self):
        import time
        before = time.time()
        entry = _make_entry()
        assert entry.created_at >= before


# ---------------------------------------------------------------------------
# ReplayQueue
# ---------------------------------------------------------------------------

class TestReplayQueue:
    def _make_queue(self, tmp_path, max_entries=100):
        cfg = ReplayConfig(path=str(tmp_path / "replay.jsonl"), max_entries=max_entries)
        return ReplayQueue(cfg)

    def test_load_returns_empty_when_no_file(self, tmp_path):
        q = self._make_queue(tmp_path)
        assert q.load() == []

    def test_push_persists_entry(self, tmp_path):
        q = self._make_queue(tmp_path)
        q.push(_make_entry())
        entries = q.load()
        assert len(entries) == 1
        assert entries[0].exit_code == 1

    def test_push_multiple_entries(self, tmp_path):
        q = self._make_queue(tmp_path)
        q.push(_make_entry(exit_code=1))
        q.push(_make_entry(exit_code=2))
        entries = q.load()
        assert len(entries) == 2
        assert entries[1].exit_code == 2

    def test_max_entries_enforced(self, tmp_path):
        q = self._make_queue(tmp_path, max_entries=3)
        for i in range(5):
            q.push(_make_entry(exit_code=i))
        entries = q.load()
        assert len(entries) == 3
        # oldest should be trimmed; last 3 exit codes are 2,3,4
        assert entries[0].exit_code == 2

    def test_clear_removes_file(self, tmp_path):
        q = self._make_queue(tmp_path)
        q.push(_make_entry())
        q.clear()
        assert q.load() == []

    def test_clear_is_idempotent(self, tmp_path):
        q = self._make_queue(tmp_path)
        q.clear()  # file does not exist yet — should not raise

    def test_file_is_valid_jsonl(self, tmp_path):
        q = self._make_queue(tmp_path)
        q.push(_make_entry(command=["ls", "-la"]))
        path = tmp_path / "replay.jsonl"
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["command"] == ["ls", "-la"]
