"""Attach throttle checking to the HookRegistry so the executor respects
rate limits between retry attempts.
"""

from __future__ import annotations

import time

from retryctl.hooks import HookContext, HookRegistry
from retryctl.throttle import SlidingWindowThrottle, ThrottleExceeded


def attach_throttle_hooks(
    registry: HookRegistry,
    throttle: SlidingWindowThrottle,
) -> None:
    """Wire *throttle* into *registry*.

    - Records each attempt failure so the window stays current.
    - Checks the throttle before each retry; if the limit is exceeded the
      hook sleeps for the required ``retry_after`` duration and then
      re-raises :exc:`ThrottleExceeded` so the caller can surface it.
    """

    def _on_attempt_failure(ctx: HookContext) -> None:
        throttle.record()

    def _on_retry(ctx: HookContext) -> None:
        try:
            throttle.check()
        except ThrottleExceeded as exc:
            if exc.retry_after > 0:
                time.sleep(exc.retry_after)
            raise

    registry.register_on_attempt_failure(_on_attempt_failure)
    registry.register_on_retry(_on_retry)
