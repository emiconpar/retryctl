"""Tests for retryctl.dryrun and retryctl.dryrun_hook."""

from __future__ import annotations

import pytest

from retryctl.dryrun import DryRunConfig, DryRunLog, DryRunRecord
from retryctl.dryrun_hook import attach_dryrun_hooks
from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult


def _make_result(exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        succeeded=exit_code == 0,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
    )


def _make_ctx(attempt: int = 1) -> HookContext:
    return HookContext(attempt_number=attempt, max_attempts=3, elapsed=0.0)


# ---------------------------------------------------------------------------
# DryRunConfig
# ---------------------------------------------------------------------------

class TestDryRunConfig:
    def test_valid_config_accepted(self):
        cfg = DryRunConfig(enabled=True, simulated_exit_code=0)
        assert cfg.enabled is True

    def test_non_bool_enabled_raises(self):
        with pytest.raises(TypeError):
            DryRunConfig(enabled="yes")  # type: ignore[arg-type]

    def test_non_int_exit_code_raises(self):
        with pytest.raises(TypeError):
            DryRunConfig(simulated_exit_code="0")  # type: ignore[arg-type]

    def test_defaults_are_safe(self):
        cfg = DryRunConfig()
        assert cfg.enabled is False
        assert cfg.simulated_exit_code == 0


# ---------------------------------------------------------------------------
# DryRunLog
# ---------------------------------------------------------------------------

class TestDryRunLog:
    def test_record_appends_entry(self):
        log = DryRunLog()
        log.record(attempt=1, command=["echo", "hi"], exit_code=0)
        assert len(log.all_records()) == 1

    def test_record_returns_dry_run_record(self):
        log = DryRunLog()
        rec = log.record(attempt=2, command=["false"], exit_code=1)
        assert isinstance(rec, DryRunRecord)
        assert rec.attempt == 2
        assert rec.simulated_exit_code == 1

    def test_to_dict_has_expected_keys(self):
        log = DryRunLog()
        rec = log.record(attempt=1, command=["ls"], exit_code=0)
        d = rec.to_dict()
        assert "attempt" in d
        assert "command" in d
        assert "simulated_exit_code" in d
        assert "note" in d

    def test_summary_contains_attempt_count(self):
        log = DryRunLog()
        log.record(1, ["cmd"], 0)
        log.record(2, ["cmd"], 1)
        summary = log.summary()
        assert "2 simulated attempt" in summary


# ---------------------------------------------------------------------------
# attach_dryrun_hooks
# ---------------------------------------------------------------------------

class TestAttachDryrunHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.log = DryRunLog()
        self.config = DryRunConfig(enabled=True, verbose=False)
        self.command = ["echo", "hello"]
        attach_dryrun_hooks(self.registry, self.config, self.log, self.command)

    def test_disabled_attaches_no_hooks(self):
        registry = HookRegistry()
        log = DryRunLog()
        attach_dryrun_hooks(registry, DryRunConfig(enabled=False), log, ["cmd"])
        registry.fire_on_success(_make_result(0), _make_ctx())
        assert len(log.all_records()) == 0

    def test_on_final_failure_records_entry(self):
        self.registry.fire_on_final_failure(_make_result(1), _make_ctx(3))
        assert len(self.log.all_records()) == 1

    def test_on_success_records_entry(self):
        self.registry.fire_on_success(_make_result(0), _make_ctx(1))
        assert len(self.log.all_records()) == 1
        assert self.log.all_records()[0].attempt == 1
