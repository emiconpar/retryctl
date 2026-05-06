"""Correlation ID generation and propagation for retry runs."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CorrelationConfig:
    """Configuration for correlation ID behaviour."""

    prefix: str = ""
    inject_env: bool = True
    env_var: str = "RETRYCTL_CORRELATION_ID"

    def __post_init__(self) -> None:
        if self.env_var and not self.env_var.strip():
            raise ValueError("env_var must not be blank")


@dataclass
class CorrelationContext:
    """Holds the correlation ID for a single retry run."""

    correlation_id: str
    config: CorrelationConfig = field(default_factory=CorrelationConfig)

    @classmethod
    def generate(cls, config: Optional[CorrelationConfig] = None) -> "CorrelationContext":
        """Generate a new correlation ID using the given config."""
        cfg = config or CorrelationConfig()
        raw = str(uuid.uuid4())
        cid = f"{cfg.prefix}{raw}" if cfg.prefix else raw
        return cls(correlation_id=cid, config=cfg)

    def env_mapping(self) -> dict[str, str]:
        """Return environment variable mapping to inject into subprocesses."""
        if not self.config.inject_env:
            return {}
        return {self.config.env_var: self.correlation_id}


def new_correlation_id(prefix: str = "") -> str:
    """Convenience function: return a fresh correlation ID string."""
    return CorrelationContext.generate(CorrelationConfig(prefix=prefix)).correlation_id
