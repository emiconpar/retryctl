"""Tests for the dead-letter hook integration."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from retryctl.deadletter import DeadLetterConfig, DeadLetterQueue
from retryctl.deadletter_hook import attach_deadletter_hooks
from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult


def _make_result(**kwargs) -> ExecutionResult:
    defaults = dict(
        command=["false"],
        exit_code=1,
        stdout="",
        stderr="",
        succeeded=False,
        attempts=3,
        total_delay=0.0,
    )
    defaults.update(kwargs)
    return ExecutionResult(**defaults)


def _make_ctx(attempt: int = 3) -> HookContext:
    return HookContext(attempt=attempt, delay=0.0, command=["false"])


class TestAttachDeadletterHooks:
    def setup_method(self):
        self.registry = HookRegistry()

    def _make_queue(self, tmp_path):
        return DeadLetterQueue(DeadLetterConfig(path=str(tmp_path)))

    def test_final_failure_pushes_entry(self, tmp_path):
        q = self._make_queue(tmp_path)
        attach_deadletter_hooks(self.registry, q)
        result = _make_result()
        self.registry.fire_final_failure(result, _make_ctx())
        entries = q.all()
        assert len(entries) == 1
        assert entries[0].exit_code == 1

    def test_entry_captures_attempt_count(self, tmp_path):
        q = self._make_queue(tmp_path)
        attach_deadletter_hooks(self.registry, q)
        self.registry.fire_final_failure(_make_result(), _make_ctx(attempt=5))
        assert q.all()[0].attempts == 5

    def test_labels_attached_to_entry(self, tmp_path):
        q = self._make_queue(tmp_path)
        attach_deadletter_hooks(self.registry, q, labels={"env": "prod"})
        self.registry.fire_final_failure(_make_result(), _make_ctx())
        assert q.all()[0].labels == {"env": "prod"}

    def test_no_push_on_retry(self, tmp_path):
        q = self._make_queue(tmp_path)
        attach_deadletter_hooks(self.registry, q)
        self.registry.fire_retry(_make_result(), _make_ctx())
        assert q.all() == []

    def test_no_push_on_attempt_failure(self, tmp_path):
        q = self._make_queue(tmp_path)
        attach_deadletter_hooks(self.registry, q)
        self.registry.fire_attempt_failure(_make_result(), _make_ctx())
        assert q.all() == []
