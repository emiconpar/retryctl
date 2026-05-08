"""Tests for retryctl.snapshot_hook."""
from unittest.mock import MagicMock

from retryctl.executor import ExecutionResult
from retryctl.hooks import HookContext, HookRegistry
from retryctl.snapshot import RunSnapshot
from retryctl.snapshot_hook import attach_snapshot_hooks


def _make_result(exit_code: int = 1, succeeded: bool = False) -> ExecutionResult:
    return ExecutionResult(
        succeeded=succeeded,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
    )


def _make_ctx(attempt_number: int = 1, next_delay: float = 0.0) -> HookContext:
    ctx = MagicMock(spec=HookContext)
    ctx.attempt_number = attempt_number
    ctx.next_delay = next_delay
    return ctx


class TestAttachSnapshotHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.snapshot = RunSnapshot(command=["false"])
        attach_snapshot_hooks(self.registry, self.snapshot)

    def test_attempt_failure_records_entry(self):
        result = _make_result(exit_code=2, succeeded=False)
        ctx = _make_ctx(attempt_number=1)
        self.registry.fire_on_attempt_failure(result, ctx)
        assert self.snapshot.total_attempts() == 1
        assert self.snapshot.entries[0].exit_code == 2
        assert self.snapshot.entries[0].succeeded is False

    def test_retry_updates_delay_on_last_entry(self):
        result = _make_result()
        ctx_fail = _make_ctx(attempt_number=1, next_delay=0.0)
        self.registry.fire_on_attempt_failure(result, ctx_fail)

        ctx_retry = _make_ctx(attempt_number=1, next_delay=2.5)
        self.registry.fire_on_retry(result, ctx_retry)

        assert self.snapshot.entries[0].delay_after == 2.5

    def test_final_failure_marks_snapshot(self):
        result = _make_result()
        ctx = _make_ctx()
        self.registry.fire_on_final_failure(result, ctx)
        assert self.snapshot.final_succeeded is False

    def test_success_records_entry_and_marks_succeeded(self):
        result = _make_result(exit_code=0, succeeded=True)
        ctx = _make_ctx(attempt_number=2)
        self.registry.fire_on_success(result, ctx)
        assert self.snapshot.total_attempts() == 1
        assert self.snapshot.entries[0].succeeded is True
        assert self.snapshot.final_succeeded is True

    def test_multiple_failures_then_success(self):
        fail_result = _make_result(exit_code=1)
        for i in range(1, 3):
            self.registry.fire_on_attempt_failure(fail_result, _make_ctx(attempt_number=i))
        ok_result = _make_result(exit_code=0, succeeded=True)
        self.registry.fire_on_success(ok_result, _make_ctx(attempt_number=3))
        assert self.snapshot.total_attempts() == 3
        assert self.snapshot.final_succeeded is True
