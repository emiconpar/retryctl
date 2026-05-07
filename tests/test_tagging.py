"""Tests for retryctl.tagging."""
import pytest

from retryctl.tagging import AttemptTags, TaggingConfig, build_tags


class TestTaggingConfig:
    def test_valid_config_accepted(self):
        cfg = TaggingConfig(static_tags={"env": "prod"}, prefix="retry_")
        assert cfg.static_tags == {"env": "prod"}

    def test_blank_key_raises(self):
        with pytest.raises(ValueError):
            TaggingConfig(static_tags={" ": "v"})

    def test_non_string_value_raises(self):
        with pytest.raises(TypeError):
            TaggingConfig(static_tags={"k": 123})  # type: ignore[dict-item]

    def test_non_dict_raises(self):
        with pytest.raises(TypeError):
            TaggingConfig(static_tags="bad")  # type: ignore[arg-type]


class TestBuildTags:
    def test_static_tags_included(self):
        cfg = TaggingConfig(static_tags={"service": "web"})
        tags = build_tags(cfg, attempt_number=1)
        assert tags.get("service") == "web"

    def test_attempt_number_included_by_default(self):
        cfg = TaggingConfig()
        tags = build_tags(cfg, attempt_number=3)
        assert tags.get("attempt") == "3"

    def test_attempt_number_excluded_when_disabled(self):
        cfg = TaggingConfig(include_attempt_number=False)
        tags = build_tags(cfg, attempt_number=3)
        assert tags.get("attempt") is None

    def test_exit_code_included_when_present(self):
        cfg = TaggingConfig()
        tags = build_tags(cfg, attempt_number=1, exit_code=2)
        assert tags.get("exit_code") == "2"

    def test_exit_code_absent_when_none(self):
        cfg = TaggingConfig()
        tags = build_tags(cfg, attempt_number=1, exit_code=None)
        assert tags.get("exit_code") is None

    def test_exit_code_excluded_when_disabled(self):
        cfg = TaggingConfig(include_exit_code=False)
        tags = build_tags(cfg, attempt_number=1, exit_code=1)
        assert tags.get("exit_code") is None

    def test_prefix_applied_to_all_keys(self):
        cfg = TaggingConfig(static_tags={"env": "ci"}, prefix="r_")
        tags = build_tags(cfg, attempt_number=2, exit_code=0)
        assert tags.get("r_env") == "ci"
        assert tags.get("r_attempt") == "2"
        assert tags.get("r_exit_code") == "0"
        assert tags.get("env") is None

    def test_all_returns_copy(self):
        cfg = TaggingConfig(static_tags={"k": "v"})
        tags = build_tags(cfg, attempt_number=1)
        d = tags.all()
        d["injected"] = "x"
        assert tags.get("injected") is None

    def test_with_tag_creates_new_instance(self):
        cfg = TaggingConfig()
        tags = build_tags(cfg, attempt_number=1)
        tags2 = tags.with_tag("extra", "yes")
        assert tags2.get("extra") == "yes"
        assert tags.get("extra") is None
