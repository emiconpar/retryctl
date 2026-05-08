"""Tests for retryctl.envmask."""
from __future__ import annotations

import os

import pytest

from retryctl.envmask import EnvMaskConfig, build_env, describe_mask


class TestEnvMaskConfig:
    def test_valid_config_accepted(self):
        cfg = EnvMaskConfig(remove=["SECRET"], override={"FOO": "bar"})
        assert cfg.remove == ["SECRET"]
        assert cfg.override == {"FOO": "bar"}

    def test_blank_remove_entry_raises(self):
        with pytest.raises(ValueError, match="non-blank"):
            EnvMaskConfig(remove=[""])

    def test_whitespace_remove_entry_raises(self):
        with pytest.raises(ValueError, match="non-blank"):
            EnvMaskConfig(remove=["   "])

    def test_blank_override_key_raises(self):
        with pytest.raises(ValueError, match="non-blank"):
            EnvMaskConfig(override={"": "value"})

    def test_clean_default_is_false(self):
        cfg = EnvMaskConfig()
        assert cfg.clean is False


class TestBuildEnv:
    def test_none_config_returns_none(self):
        assert build_env(None) is None

    def test_inherits_parent_env_by_default(self):
        os.environ["_RETRYCTL_TEST_VAR"] = "hello"
        try:
            result = build_env(EnvMaskConfig())
            assert result is not None
            assert result.get("_RETRYCTL_TEST_VAR") == "hello"
        finally:
            del os.environ["_RETRYCTL_TEST_VAR"]

    def test_remove_strips_variable(self):
        os.environ["_RETRYCTL_SECRET"] = "topsecret"
        try:
            result = build_env(EnvMaskConfig(remove=["_RETRYCTL_SECRET"]))
            assert "_RETRYCTL_SECRET" not in result
        finally:
            del os.environ["_RETRYCTL_SECRET"]

    def test_remove_missing_variable_is_noop(self):
        result = build_env(EnvMaskConfig(remove=["_RETRYCTL_NONEXISTENT_XYZ"]))
        assert result is not None  # no KeyError raised

    def test_override_sets_variable(self):
        result = build_env(EnvMaskConfig(override={"_RETRYCTL_FORCED": "42"}))
        assert result["_RETRYCTL_FORCED"] == "42"

    def test_override_replaces_existing_variable(self):
        os.environ["_RETRYCTL_ORIG"] = "original"
        try:
            result = build_env(EnvMaskConfig(override={"_RETRYCTL_ORIG": "replaced"}))
            assert result["_RETRYCTL_ORIG"] == "replaced"
        finally:
            del os.environ["_RETRYCTL_ORIG"]

    def test_clean_starts_empty(self):
        result = build_env(EnvMaskConfig(clean=True))
        assert result == {}

    def test_clean_with_override(self):
        result = build_env(EnvMaskConfig(clean=True, override={"ONLY": "this"}))
        assert result == {"ONLY": "this"}

    def test_result_is_independent_copy(self):
        result = build_env(EnvMaskConfig())
        result["_MUTATED"] = "yes"
        assert "_MUTATED" not in os.environ


class TestDescribeMask:
    def test_noop_config_description(self):
        desc = describe_mask(EnvMaskConfig())
        assert "no-op" in desc

    def test_clean_appears_in_description(self):
        desc = describe_mask(EnvMaskConfig(clean=True))
        assert "clean=True" in desc

    def test_remove_appears_in_description(self):
        desc = describe_mask(EnvMaskConfig(remove=["SECRET"]))
        assert "SECRET" in desc

    def test_override_keys_appear_in_description(self):
        desc = describe_mask(EnvMaskConfig(override={"TOKEN": "x"}))
        assert "TOKEN" in desc
