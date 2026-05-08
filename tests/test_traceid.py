"""Tests for retryctl.traceid."""
import uuid
import pytest

from retryctl.traceid import TraceIdConfig, TraceContext


class TestTraceIdConfig:
    def test_valid_config_accepted(self):
        cfg = TraceIdConfig(env_var="MY_TRACE", header_name="X-My-Trace")
        assert cfg.env_var == "MY_TRACE"
        assert cfg.header_name == "X-My-Trace"

    def test_blank_env_var_raises(self):
        with pytest.raises(ValueError, match="env_var"):
            TraceIdConfig(env_var="   ")

    def test_blank_header_name_raises(self):
        with pytest.raises(ValueError, match="header_name"):
            TraceIdConfig(header_name="")

    def test_defaults_are_sensible(self):
        cfg = TraceIdConfig()
        assert cfg.env_var == "RETRYCTL_TRACE_ID"
        assert cfg.reuse_existing is True


class TestTraceContext:
    def test_generate_produces_valid_uuid(self):
        ctx = TraceContext.generate()
        parsed = uuid.UUID(ctx.trace_id)
        assert str(parsed) == ctx.trace_id

    def test_generate_sets_parent_id(self):
        ctx = TraceContext.generate(parent_id="parent-abc")
        assert ctx.parent_id == "parent-abc"

    def test_two_generate_calls_differ(self):
        a = TraceContext.generate()
        b = TraceContext.generate()
        assert a.trace_id != b.trace_id

    def test_from_env_reuses_existing_when_configured(self):
        cfg = TraceIdConfig(reuse_existing=True)
        env = {cfg.env_var: "existing-id-123"}
        ctx = TraceContext.from_env(env, cfg)
        assert ctx.trace_id == "existing-id-123"

    def test_from_env_generates_new_when_not_reusing(self):
        cfg = TraceIdConfig(reuse_existing=False)
        env = {cfg.env_var: "existing-id-123"}
        ctx = TraceContext.from_env(env, cfg)
        assert ctx.trace_id != "existing-id-123"

    def test_from_env_generates_when_missing(self):
        cfg = TraceIdConfig(reuse_existing=True)
        ctx = TraceContext.from_env({}, cfg)
        uuid.UUID(ctx.trace_id)  # must be valid UUID

    def test_env_mapping_includes_trace_id(self):
        cfg = TraceIdConfig()
        ctx = TraceContext(trace_id="abc-123")
        mapping = ctx.env_mapping(cfg)
        assert mapping[cfg.env_var] == "abc-123"

    def test_env_mapping_includes_parent_when_set(self):
        cfg = TraceIdConfig()
        ctx = TraceContext(trace_id="abc-123", parent_id="parent-999")
        mapping = ctx.env_mapping(cfg)
        assert mapping[cfg.env_var + "_PARENT"] == "parent-999"

    def test_env_mapping_excludes_parent_when_none(self):
        cfg = TraceIdConfig()
        ctx = TraceContext(trace_id="abc-123")
        mapping = ctx.env_mapping(cfg)
        assert cfg.env_var + "_PARENT" not in mapping

    def test_to_dict_includes_trace_id(self):
        ctx = TraceContext(trace_id="xyz")
        d = ctx.to_dict()
        assert d["trace_id"] == "xyz"

    def test_to_dict_excludes_none_parent(self):
        ctx = TraceContext(trace_id="xyz")
        assert "parent_id" not in ctx.to_dict()

    def test_to_dict_includes_parent_when_set(self):
        ctx = TraceContext(trace_id="xyz", parent_id="p1")
        assert ctx.to_dict()["parent_id"] == "p1"
