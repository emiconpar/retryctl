"""Trace ID generation and propagation for retry runs."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TraceIdConfig:
    """Configuration for trace ID injection."""

    env_var: str = "RETRYCTL_TRACE_ID"
    header_name: str = "X-Trace-Id"
    reuse_existing: bool = True

    def __post_init__(self) -> None:
        if not self.env_var or not self.env_var.strip():
            raise ValueError("env_var must not be blank")
        if not self.header_name or not self.header_name.strip():
            raise ValueError("header_name must not be blank")


@dataclass
class TraceContext:
    """Holds the trace ID for a single retry run."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None

    @classmethod
    def generate(cls, parent_id: Optional[str] = None) -> "TraceContext":
        """Create a new TraceContext with a fresh UUID."""
        return cls(trace_id=str(uuid.uuid4()), parent_id=parent_id)

    @classmethod
    def from_env(cls, env: dict, config: TraceIdConfig) -> "TraceContext":
        """Reuse an existing trace ID from the environment if present."""
        existing = env.get(config.env_var)
        if config.reuse_existing and existing:
            return cls(trace_id=existing)
        return cls.generate()

    def env_mapping(self, config: TraceIdConfig) -> dict:
        """Return environment variables to inject into the child process."""
        mapping = {config.env_var: self.trace_id}
        if self.parent_id is not None:
            mapping[config.env_var + "_PARENT"] = self.parent_id
        return mapping

    def to_dict(self) -> dict:
        d: dict = {"trace_id": self.trace_id}
        if self.parent_id is not None:
            d["parent_id"] = self.parent_id
        return d
