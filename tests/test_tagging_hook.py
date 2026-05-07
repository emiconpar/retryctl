"""Tests for retryctl.tagging_hook."""
import pytest

from retryctl.executor import ExecutionResult
from retryctl.hooks import HookRegistry
from retryctl.context import RetryContext
from retryctl.tagging import TaggingConfig
from retryctl.tagging_hook import attach_tagging_hooks, _TAG_KEY


def _make_result(exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        succeeded=exit_code == 0,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        elapsed=0.1,
    )


def _make_ctx(attempt: int = 1) -> RetryContext:
    return RetryContext(max_attempts=3, attempt=attempt, extra={})


class TestAttachTaggingHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.config = TaggingConfig(static_tags={"env": "test"}, prefix="")
        attach_tagging_hooks(self.registry, self.config)

    def test_on_attempt_failure_sets_tags(self):
        result = _make_result(exit_code=2)
        ctx = _make_ctx(attempt=1)
        self.registry.fire_on_attempt_failure(result, ctx)
        assert _TAG_KEY in ctx.extra
        tags = ctx.extra[_TAG_KEY]
        assert tags.get("exit_code") == "2"
        assert tags.get("attempt") == "1"
        assert tags.get("env") == "test"

    def test_on_retry_sets_tags_when_missing(self):
        result = _make_result(exit_code=1)
        ctx = _make_ctx(attempt=2)
        self.registry.fire_on_retry(result, ctx)
        assert _TAG_KEY in ctx.extra

    def test_on_retry_does_not_overwrite_existing_tags(self):
        result = _make_result(exit_code=1)
        ctx = _make_ctx(attempt=2)
        from retryctl.tagging import AttemptTags
        sentinel = AttemptTags({"sentinel": "yes"})
        ctx.extra[_TAG_KEY] = sentinel
        self.registry.fire_on_retry(result, ctx)
        assert ctx.extra[_TAG_KEY] is sentinel

    def test_on_final_failure_sets_tags(self):
        result = _make_result(exit_code=3)
        ctx = _make_ctx(attempt=3)
        self.registry.fire_on_final_failure(result, ctx)
        tags = ctx.extra[_TAG_KEY]
        assert tags.get("exit_code") == "3"

    def test_on_success_sets_tags(self):
        result = _make_result(exit_code=0)
        ctx = _make_ctx(attempt=1)
        self.registry.fire_on_success(result, ctx)
        tags = ctx.extra[_TAG_KEY]
        assert tags.get("exit_code") == "0"
        assert tags.get("attempt") == "1"
