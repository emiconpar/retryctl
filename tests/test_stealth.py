"""Tests for retryctl.stealth."""
from __future__ import annotations

import pytest

from retryctl.stealth import StealthConfig, StealthRecord, apply_stealth


# ---------------------------------------------------------------------------
# TestStealthConfig
# ---------------------------------------------------------------------------

class TestStealthConfig:
    def test_valid_config_accepted(self):
        cfg = StealthConfig(enabled=True, suppress_headers=True, suppress_attempt_info=False)
        assert cfg.enabled is True

    def test_defaults_are_sensible(self):
        cfg = StealthConfig()
        assert cfg.enabled is True
        assert cfg.suppress_headers is True
        assert cfg.suppress_attempt_info is True
        assert cfg.hidden_env_vars == []

    def test_non_bool_enabled_raises(self):
        with pytest.raises(TypeError, match="enabled must be a bool"):
            StealthConfig(enabled="yes")  # type: ignore[arg-type]

    def test_non_bool_suppress_headers_raises(self):
        with pytest.raises(TypeError, match="suppress_headers must be a bool"):
            StealthConfig(suppress_headers=1)  # type: ignore[arg-type]

    def test_non_list_hidden_env_vars_raises(self):
        with pytest.raises(TypeError, match="hidden_env_vars must be a list"):
            StealthConfig(hidden_env_vars="SECRET")  # type: ignore[arg-type]

    def test_blank_hidden_env_var_raises(self):
        with pytest.raises(ValueError, match="non-blank strings"):
            StealthConfig(hidden_env_vars=[""])

    def test_whitespace_hidden_env_var_raises(self):
        with pytest.raises(ValueError, match="non-blank strings"):
            StealthConfig(hidden_env_vars=["   "])

    def test_valid_hidden_env_vars_accepted(self):
        cfg = StealthConfig(hidden_env_vars=["SECRET_KEY", "API_TOKEN"])
        assert len(cfg.hidden_env_vars) == 2


# ---------------------------------------------------------------------------
# TestApplyStealth
# ---------------------------------------------------------------------------

class TestApplyStealth:
    def test_disabled_returns_output_unchanged(self):
        cfg = StealthConfig(enabled=False)
        output = "[retryctl] attempt 1\nsome output\n"
        result, record = apply_stealth(cfg, output)
        assert result == output
        assert record.headers_suppressed is False

    def test_suppresses_retryctl_header_lines(self):
        cfg = StealthConfig(enabled=True, suppress_headers=True)
        output = "[retryctl] starting\nreal output\n"
        result, record = apply_stealth(cfg, output)
        assert "[retryctl]" not in result
        assert "real output" in result
        assert record.headers_suppressed is True

    def test_does_not_suppress_headers_when_disabled(self):
        cfg = StealthConfig(enabled=True, suppress_headers=False)
        output = "[retryctl] starting\nreal output\n"
        result, record = apply_stealth(cfg, output)
        assert "[retryctl]" in result
        assert record.headers_suppressed is False

    def test_suppresses_attempt_info_lines(self):
        cfg = StealthConfig(enabled=True, suppress_attempt_info=True)
        output = "retryctl attempt 2 failed\nactual output\n"
        result, record = apply_stealth(cfg, output)
        assert "attempt" not in result.lower() or "actual" in result
        assert record.attempt_info_suppressed is True

    def test_hidden_env_vars_count_recorded(self):
        cfg = StealthConfig(hidden_env_vars=["SECRET", "TOKEN"])
        _, record = apply_stealth(cfg, "some output")
        assert record.hidden_vars_count == 2

    def test_empty_output_returns_empty(self):
        cfg = StealthConfig()
        result, _ = apply_stealth(cfg, "")
        assert result == ""


# ---------------------------------------------------------------------------
# TestStealthRecord
# ---------------------------------------------------------------------------

class TestStealthRecord:
    def test_to_dict_contains_expected_keys(self):
        rec = StealthRecord(headers_suppressed=True, attempt_info_suppressed=False, hidden_vars_count=3)
        d = rec.to_dict()
        assert d["headers_suppressed"] is True
        assert d["attempt_info_suppressed"] is False
        assert d["hidden_vars_count"] == 3

    def test_defaults_are_false_and_zero(self):
        rec = StealthRecord()
        assert rec.headers_suppressed is False
        assert rec.attempt_info_suppressed is False
        assert rec.hidden_vars_count == 0
