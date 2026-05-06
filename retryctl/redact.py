"""Redaction support for masking sensitive values in command output and logs."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RedactConfig:
    """Configuration for redacting sensitive patterns from output."""

    patterns: List[str] = field(default_factory=list)
    replacement: str = "***"
    redact_env_vars: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.replacement:
            raise ValueError("replacement must not be empty")
        for pattern in self.patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"invalid regex pattern {pattern!r}: {exc}") from exc


@dataclass
class Redactor:
    """Applies redaction rules to strings."""

    config: RedactConfig
    _compiled: List[re.Pattern] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = [re.compile(p) for p in self.config.patterns]

    def redact(self, text: Optional[str]) -> Optional[str]:
        """Return *text* with all sensitive patterns replaced."""
        if text is None:
            return None
        result = text
        for pattern in self._compiled:
            result = pattern.sub(self.config.replacement, result)
        return result

    def redact_env(self, env: dict) -> dict:
        """Return a copy of *env* with sensitive variable values masked."""
        redacted = dict(env)
        for key in self.config.redact_env_vars:
            if key in redacted:
                redacted[key] = self.config.replacement
        return redacted


def build_redactor(config: Optional[RedactConfig]) -> Optional[Redactor]:
    """Return a :class:`Redactor` for *config*, or ``None`` if config is absent."""
    if config is None:
        return None
    return Redactor(config=config)
