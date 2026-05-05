"""Tests for retryctl.concurrency."""
from __future__ import annotations

import threading
import pytest

from retryctl.concurrency import (
    ConcurrencyConfig,
    ConcurrencyLimiter,
    ConcurrencyLimitExceeded,
)


# ---------------------------------------------------------------------------
# ConcurrencyConfig validation
# ---------------------------------------------------------------------------

class TestConcurrencyConfig:
    def test_valid_config_accepted(self) -> None:
        cfg = ConcurrencyConfig(max_concurrent=3)
        assert cfg.max_concurrent == 3

    def test_zero_max_concurrent_raises(self) -> None:
        with pytest.raises(ValueError):
            ConcurrencyConfig(max_concurrent=0)

    def test_negative_max_concurrent_raises(self) -> None:
        with pytest.raises(ValueError):
            ConcurrencyConfig(max_concurrent=-1)


# ---------------------------------------------------------------------------
# ConcurrencyLimiter behaviour
# ---------------------------------------------------------------------------

def _make_limiter(max_concurrent: int = 2) -> ConcurrencyLimiter:
    return ConcurrencyLimiter(config=ConcurrencyConfig(max_concurrent=max_concurrent))


class TestConcurrencyLimiter:
    def test_initial_active_is_zero(self) -> None:
        limiter = _make_limiter()
        assert limiter.active == 0

    def test_acquire_increments_active(self) -> None:
        limiter = _make_limiter()
        limiter.acquire()
        assert limiter.active == 1

    def test_release_decrements_active(self) -> None:
        limiter = _make_limiter()
        limiter.acquire()
        limiter.release()
        assert limiter.active == 0

    def test_release_below_zero_clamps_to_zero(self) -> None:
        limiter = _make_limiter()
        limiter.release()  # should not go negative
        assert limiter.active == 0

    def test_exceeding_limit_raises(self) -> None:
        limiter = _make_limiter(max_concurrent=1)
        limiter.acquire()
        with pytest.raises(ConcurrencyLimitExceeded) as exc_info:
            limiter.acquire()
        assert exc_info.value.limit == 1

    def test_context_manager_acquires_and_releases(self) -> None:
        limiter = _make_limiter()
        with limiter:
            assert limiter.active == 1
        assert limiter.active == 0

    def test_context_manager_releases_on_exception(self) -> None:
        limiter = _make_limiter()
        try:
            with limiter:
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert limiter.active == 0

    def test_thread_safety(self) -> None:
        """Concurrent acquires must never exceed the cap."""
        limiter = _make_limiter(max_concurrent=5)
        errors: list[Exception] = []
        successes: list[int] = []

        def worker() -> None:
            try:
                with limiter:
                    successes.append(1)
            except ConcurrencyLimitExceeded as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert limiter.active == 0
        assert len(successes) + len(errors) == 10
