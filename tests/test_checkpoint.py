"""Tests for retryctl.checkpoint."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from retryctl.checkpoint import CheckpointState, CheckpointStore


def _make_state(**kwargs) -> CheckpointState:
    defaults = dict(
        command=["echo", "hi"],
        attempt=1,
        total_delay=0.5,
        last_exit_code=1,
    )
    defaults.update(kwargs)
    return CheckpointState(**defaults)


class TestCheckpointState:
    def test_to_dict_round_trips(self):
        state = _make_state()
        assert CheckpointState.from_dict(state.to_dict()) == state

    def test_optional_exit_code_none(self):
        state = _make_state(last_exit_code=None)
        d = state.to_dict()
        assert d["last_exit_code"] is None

    def test_created_at_is_recent(self):
        before = time.time()
        state = _make_state()
        assert state.created_at >= before


class TestCheckpointStore:
    def test_save_and_load(self, tmp_path):
        path = tmp_path / "checkpoint.json"
        store = CheckpointStore(path)
        state = _make_state(attempt=3, total_delay=2.0)
        store.save(state)
        loaded = store.load()
        assert loaded is not None
        assert loaded.attempt == 3
        assert loaded.total_delay == 2.0
        assert loaded.command == ["echo", "hi"]

    def test_load_returns_none_when_missing(self, tmp_path):
        store = CheckpointStore(tmp_path / "nope.json")
        assert store.load() is None

    def test_load_returns_none_on_corrupt_file(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json{{{")
        store = CheckpointStore(path)
        assert store.load() is None

    def test_clear_removes_file(self, tmp_path):
        path = tmp_path / "checkpoint.json"
        store = CheckpointStore(path)
        store.save(_make_state())
        assert store.exists
        store.clear()
        assert not store.exists

    def test_clear_is_idempotent(self, tmp_path):
        store = CheckpointStore(tmp_path / "checkpoint.json")
        store.clear()  # should not raise

    def test_save_is_atomic_via_tmp(self, tmp_path):
        path = tmp_path / "checkpoint.json"
        store = CheckpointStore(path)
        store.save(_make_state())
        assert not (tmp_path / "checkpoint.tmp").exists()
        assert path.exists()
