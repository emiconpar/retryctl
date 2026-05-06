"""Tests for retryctl.redact and retryctl.redact_hook."""
from __future__ import annotations

import pytest

from retryctl.redact import RedactConfig, Redactor, build_redactor
from retryctl.redact_hook import attach_redact_hooks
from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(stdout="output", stderr="error") -> ExecutionResult:
    return ExecutionResult(
        succeeded=False,
        exit_code=1,
        stdout=stdout,
        stderr=stderr,
        attempts=1,
    )


def _make_ctx() -> HookContext:
    return HookContext(attempt=1, max_attempts=3, delay=0.0, labels={})


# ---------------------------------------------------------------------------
# RedactConfig validation
# ---------------------------------------------------------------------------

class TestRedactConfig:
    def test_valid_config_accepted(self):
        cfg = RedactConfig(patterns=[r"secret-\w+"], replacement="[REDACTED]")
        assert cfg.replacement == "[REDACTED]"

    def test_empty_replacement_raises(self):
        with pytest.raises(ValueError, match="replacement"):
            RedactConfig(replacement="")

    def test_invalid_pattern_raises(self):
        with pytest.raises(ValueError, match="invalid regex"):
            RedactConfig(patterns=["["])


# ---------------------------------------------------------------------------
# Redactor.redact
# ---------------------------------------------------------------------------

class TestRedactor:
    def _make(self, patterns=None, replacement="***", env_vars=None):
        cfg = RedactConfig(
            patterns=patterns or [],
            replacement=replacement,
            redact_env_vars=env_vars or [],
        )
        return Redactor(config=cfg)

    def test_none_input_returns_none(self):
        r = self._make()
        assert r.redact(None) is None

    def test_no_match_unchanged(self):
        r = self._make(patterns=[r"secret"])
        assert r.redact("hello world") == "hello world"

    def test_matching_pattern_replaced(self):
        r = self._make(patterns=[r"password=\S+"], replacement="password=***")
        assert r.redact("cmd password=hunter2 --verbose") == "cmd password=*** --verbose"

    def test_multiple_patterns_applied(self):
        r = self._make(patterns=[r"token=\S+", r"key=\S+"], replacement="[X]")
        result = r.redact("token=abc key=def rest")
        assert "abc" not in result
        assert "def" not in result

    def test_redact_env_masks_value(self):
        r = self._make(env_vars=["SECRET_KEY"])
        env = {"SECRET_KEY": "supersecret", "PATH": "/usr/bin"}
        out = r.redact_env(env)
        assert out["SECRET_KEY"] == "***"
        assert out["PATH"] == "/usr/bin"

    def test_redact_env_ignores_missing_keys(self):
        r = self._make(env_vars=["MISSING"])
        env = {"PATH": "/usr/bin"}
        out = r.redact_env(env)
        assert out == env


# ---------------------------------------------------------------------------
# build_redactor
# ---------------------------------------------------------------------------

def test_build_redactor_none_returns_none():
    assert build_redactor(None) is None


def test_build_redactor_returns_redactor():
    cfg = RedactConfig(patterns=[r"\d+"])
    r = build_redactor(cfg)
    assert isinstance(r, Redactor)


# ---------------------------------------------------------------------------
# redact_hook
# ---------------------------------------------------------------------------

class TestAttachRedactHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        cfg = RedactConfig(patterns=[r"secret"], replacement="***")
        self.redactor = Redactor(config=cfg)
        attach_redact_hooks(self.registry, self.redactor)

    def test_stdout_redacted_on_attempt_failure(self):
        result = _make_result(stdout="contains secret here")
        self.registry.fire_on_attempt_failure(result, _make_ctx())
        assert "secret" not in result.stdout

    def test_stderr_redacted_on_retry(self):
        result = _make_result(stderr="secret in stderr")
        self.registry.fire_on_retry(result, _make_ctx())
        assert "secret" not in result.stderr

    def test_no_crash_when_stdout_none(self):
        result = _make_result(stdout=None, stderr=None)
        self.registry.fire_on_final_failure(result, _make_ctx())  # should not raise
