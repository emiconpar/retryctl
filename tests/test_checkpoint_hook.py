"""Tests for retryctl.checkpoint_hook."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from retryctl.checkpoint import CheckpointStore
from retryctl.checkpoint_hook import attach_checkpoint_hooks
from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult


def _make_result(exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        succeeded=exit_code == 0,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        total_duration=0.1,
    )


def _make_ctx(attempt: int = 1, total_delay: float = 0.0) -> HookContext:
    return HookContext(
        command=["false"],
        attempt=attempt,
        max_attempts=3,
        total_delay=total_delay,
    )


class TestAttachCheckpointHooks:
    def setup_method(self):
        self.registry = HookRegistry()

    def _make_store(self, tmp_path: Path) -> CheckpointStore:
        return CheckpointStore(tmp_path / "checkpoint.json")

    def test_attempt_failure_saves_state(self, tmp_path):
        store = self._make_store(tmp_path)
        attach_checkpoint_hooks(self.registry, store)
        self.registry.fire_on_attempt_failure(_make_result(exit_code=2), _make_ctx(attempt=1))
        state = store.load()
        assert state is not None
        assert state.attempt == 1
        assert state.last_exit_code == 2

    def test_retry_updates_attempt(self, tmp_path):
        store = self._make_store(tmp_path)
        attach_checkpoint_hooks(self.registry, store)
        self.registry.fire_on_attempt_failure(_make_result(), _make_ctx(attempt=1))
        self.registry.fire_on_retry(_make_result(), _make_ctx(attempt=2, total_delay=1.5))
        state = store.load()
        assert state is not None
        assert state.attempt == 2
        assert state.total_delay == 1.5

    def test_final_failure_clears_state(self, tmp_path):
        store = self._make_store(tmp_path)
        attach_checkpoint_hooks(self.registry, store)
        self.registry.fire_on_attempt_failure(_make_result(), _make_ctx())
        assert store.exists
        self.registry.fire_on_final_failure(_make_result(), _make_ctx())
        assert not store.exists

    def test_success_clears_state(self, tmp_path):
        store = self._make_store(tmp_path)
        attach_checkpoint_hooks(self.registry, store)
        self.registry.fire_on_attempt_failure(_make_result(), _make_ctx())
        assert store.exists
        self.registry.fire_on_success(_make_result(exit_code=0), _make_ctx())
        assert not store.exists
