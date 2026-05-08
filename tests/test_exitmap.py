"""Tests for retryctl.exitmap."""
import pytest

from retryctl.exitmap import ExitMapConfig, ExitCodeLabel, ExitMapper


# ---------------------------------------------------------------------------
# ExitMapConfig validation
# ---------------------------------------------------------------------------

class TestExitMapConfig:
    def test_valid_config_accepted(self):
        cfg = ExitMapConfig(mapping={0: "ok", 1: "error"}, default_label="unknown")
        assert cfg.mapping[0] == "ok"

    def test_empty_mapping_accepted(self):
        cfg = ExitMapConfig()
        assert cfg.mapping == {}

    def test_non_dict_mapping_raises(self):
        with pytest.raises(TypeError, match="mapping must be a dict"):
            ExitMapConfig(mapping="bad")  # type: ignore[arg-type]

    def test_non_int_key_raises(self):
        with pytest.raises(TypeError, match="exit code key must be int"):
            ExitMapConfig(mapping={"1": "ok"})  # type: ignore[dict-item]

    def test_blank_label_raises(self):
        with pytest.raises(ValueError, match="label for code"):
            ExitMapConfig(mapping={1: "   "})

    def test_empty_label_raises(self):
        with pytest.raises(ValueError, match="label for code"):
            ExitMapConfig(mapping={1: ""})

    def test_blank_default_label_raises(self):
        with pytest.raises(ValueError, match="default_label"):
            ExitMapConfig(default_label="  ")


# ---------------------------------------------------------------------------
# ExitMapper.lookup
# ---------------------------------------------------------------------------

def _make_mapper(**kwargs) -> ExitMapper:
    return ExitMapper(ExitMapConfig(**kwargs))


class TestExitMapperLookup:
    def test_known_code_returns_configured_label(self):
        mapper = _make_mapper(mapping={0: "success", 1: "general_error"})
        result = mapper.lookup(0)
        assert result.label == "success"
        assert result.is_default is False

    def test_unknown_code_returns_default_label(self):
        mapper = _make_mapper(mapping={0: "ok"}, default_label="unknown")
        result = mapper.lookup(99)
        assert result.label == "unknown"
        assert result.is_default is True

    def test_result_carries_original_code(self):
        mapper = _make_mapper(mapping={2: "misuse"})
        result = mapper.lookup(2)
        assert result.code == 2

    def test_to_dict_includes_all_fields(self):
        mapper = _make_mapper(mapping={1: "err"})
        d = mapper.lookup(1).to_dict()
        assert d == {"code": 1, "label": "err", "is_default": False}

    def test_default_to_dict_marks_is_default(self):
        mapper = _make_mapper(default_label="fallback")
        d = mapper.lookup(42).to_dict()
        assert d["is_default"] is True
        assert d["label"] == "fallback"


class TestExitMapperHelpers:
    def test_known_codes_returns_copy(self):
        mapper = _make_mapper(mapping={0: "ok", 1: "err"})
        codes = mapper.known_codes()
        assert codes == {0: "ok", 1: "err"}
        # mutating the returned dict must not affect the mapper
        codes[99] = "extra"
        assert 99 not in mapper.known_codes()

    def test_describe_with_mappings(self):
        mapper = _make_mapper(mapping={0: "ok"}, default_label="unknown")
        desc = mapper.describe()
        assert "0=" in desc
        assert "unknown" in desc

    def test_describe_empty_mapping(self):
        mapper = _make_mapper()
        desc = mapper.describe()
        assert "no explicit mappings" in desc
