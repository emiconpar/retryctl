"""Tests for retryctl.audit_hook — hook integration."""
from __future__ import annotations

import pytest

from retryctl.audit import AuditLog
from retryctl.audit_hook import attach_audit_hooks
from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult


def _make_result(exit_code: int = 1, succeeded: bool = False) -> ExecutionResult:
    return ExecutionResult(
        succeeded=succeeded,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        total_delay=0.0,
    )


def _make_ctx(attempt: int = 1, next_delay: float = 1.0) -> HookContext:
    return HookContext(attempt_number=attempt, next_delay=next_delay, command=["false"])


class TestAttachAuditHooks:
    def setup_method(self):
        self.log = AuditLog(command=["false"])
        self.registry = HookRegistry()
        attach_audit_hooks(self.registry, self.log)

    def test_attempt_failure_records_event(self):
        self.registry.fire_on_attempt_failure(_make_result(), _make_ctx(attempt=1))
        assert len(self.log.events) == 1
        assert self.log.events[0].note == "attempt_failure"

    def test_retry_records_delay(self):
        self.registry.fire_on_retry(_make_result(), _make_ctx(attempt=1, next_delay=3.0))
        assert self.log.events[0].delay_before_next == 3.0
        assert self.log.events[0].note == "retry_scheduled"

    def test_final_failure_note(self):
        self.registry.fire_on_final_failure(_make_result(), _make_ctx(attempt=3))
        assert self.log.events[0].note == "final_failure"
        assert self.log.events[0].attempt == 3

    def test_success_note(self):
        result = _make_result(exit_code=0, succeeded=True)
        self.registry.fire_on_success(result, _make_ctx(attempt=2))
        assert self.log.events[0].note == "success"
        assert self.log.events[0].succeeded is True

    def test_multiple_hooks_accumulate(self):
        self.registry.fire_on_attempt_failure(_make_result(), _make_ctx(attempt=1))
        self.registry.fire_on_retry(_make_result(), _make_ctx(attempt=1))
        self.registry.fire_on_final_failure(_make_result(), _make_ctx(attempt=2))
        assert len(self.log.events) == 3
