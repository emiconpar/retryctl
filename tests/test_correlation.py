"""Tests for retryctl.correlation."""
from __future__ import annotations

import pytest

from retryctl.correlation import (
    CorrelationConfig,
    CorrelationContext,
    new_correlation_id,
)


class TestCorrelationConfig:
    def test_valid_config_accepted(self) -> None:
        cfg = CorrelationConfig(prefix="run-", inject_env=True, env_var="MY_CID")
        assert cfg.prefix == "run-"

    def test_blank_env_var_raises(self) -> None:
        with pytest.raises(ValueError, match="env_var"):
            CorrelationConfig(env_var="   ")

    def test_empty_prefix_allowed(self) -> None:
        cfg = CorrelationConfig(prefix="")
        assert cfg.prefix == ""


class TestCorrelationContext:
    def test_generate_returns_context(self) -> None:
        ctx = CorrelationContext.generate()
        assert isinstance(ctx.correlation_id, str)
        assert len(ctx.correlation_id) > 0

    def test_prefix_prepended(self) -> None:
        cfg = CorrelationConfig(prefix="test-")
        ctx = CorrelationContext.generate(cfg)
        assert ctx.correlation_id.startswith("test-")

    def test_no_prefix_is_plain_uuid(self) -> None:
        ctx = CorrelationContext.generate(CorrelationConfig(prefix=""))
        # UUID4 has exactly 36 chars (with dashes)
        assert len(ctx.correlation_id) == 36

    def test_each_call_unique(self) -> None:
        a = CorrelationContext.generate()
        b = CorrelationContext.generate()
        assert a.correlation_id != b.correlation_id

    def test_env_mapping_when_inject_true(self) -> None:
        cfg = CorrelationConfig(inject_env=True, env_var="MY_VAR")
        ctx = CorrelationContext.generate(cfg)
        mapping = ctx.env_mapping()
        assert mapping == {"MY_VAR": ctx.correlation_id}

    def test_env_mapping_when_inject_false(self) -> None:
        cfg = CorrelationConfig(inject_env=False)
        ctx = CorrelationContext.generate(cfg)
        assert ctx.env_mapping() == {}


class TestNewCorrelationId:
    def test_returns_string(self) -> None:
        cid = new_correlation_id()
        assert isinstance(cid, str)

    def test_prefix_applied(self) -> None:
        cid = new_correlation_id(prefix="job-")
        assert cid.startswith("job-")

    def test_unique_per_call(self) -> None:
        assert new_correlation_id() != new_correlation_id()
