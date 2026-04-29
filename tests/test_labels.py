"""Tests for retryctl.labels."""
import pytest

from retryctl.labels import LabelSet, parse_labels


# ---------------------------------------------------------------------------
# LabelSet
# ---------------------------------------------------------------------------

class TestLabelSetGet:
    def test_returns_value_for_present_key(self):
        ls = LabelSet({"env": "prod"})
        assert ls.get("env") == "prod"

    def test_returns_none_for_missing_key(self):
        ls = LabelSet()
        assert ls.get("missing") is None


class TestLabelSetAll:
    def test_returns_copy(self):
        ls = LabelSet({"a": "1"})
        copy = ls.all()
        copy["b"] = "2"
        assert "b" not in ls

    def test_empty_by_default(self):
        assert LabelSet().all() == {}


class TestLabelSetWithLabel:
    def test_adds_new_label(self):
        ls = LabelSet().with_label("region", "us-east-1")
        assert ls.get("region") == "us-east-1"

    def test_overwrites_existing_label(self):
        ls = LabelSet({"env": "staging"}).with_label("env", "prod")
        assert ls.get("env") == "prod"

    def test_original_unchanged(self):
        original = LabelSet({"env": "staging"})
        original.with_label("env", "prod")
        assert original.get("env") == "staging"

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="key must not be empty"):
            LabelSet().with_label("", "value")


class TestLabelSetMerge:
    def test_combines_disjoint_labels(self):
        a = LabelSet({"x": "1"})
        b = LabelSet({"y": "2"})
        merged = a.merge(b)
        assert merged.all() == {"x": "1", "y": "2"}

    def test_other_wins_on_conflict(self):
        a = LabelSet({"k": "old"})
        b = LabelSet({"k": "new"})
        assert a.merge(b).get("k") == "new"


class TestLabelSetContains:
    def test_present_key(self):
        ls = LabelSet({"a": "1"})
        assert "a" in ls

    def test_missing_key(self):
        assert "z" not in LabelSet()


# ---------------------------------------------------------------------------
# parse_labels
# ---------------------------------------------------------------------------

class TestParseLabels:
    def test_parses_single_label(self):
        ls = parse_labels(["env=prod"])
        assert ls.get("env") == "prod"

    def test_parses_multiple_labels(self):
        ls = parse_labels(["env=prod", "region=us-east-1"])
        assert ls.get("region") == "us-east-1"

    def test_value_may_contain_equals(self):
        ls = parse_labels(["tag=a=b"])
        assert ls.get("tag") == "a=b"

    def test_missing_equals_raises(self):
        with pytest.raises(ValueError, match="expected 'key=value' format"):
            parse_labels(["badlabel"])

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="key must not be empty"):
            parse_labels(["=value"])

    def test_empty_list_returns_empty_labelset(self):
        assert len(parse_labels([])) == 0
