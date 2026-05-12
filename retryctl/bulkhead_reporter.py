"""Reporters for bulkhead state."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Dict

from retryctl.bulkhead import BulkheadRegistry


class BulkheadReporter(ABC):
    @abstractmethod
    def report(self, registry: BulkheadRegistry, keys: list[str]) -> str:
        ...


class NullBulkheadReporter(BulkheadReporter):
    def report(self, registry: BulkheadRegistry, keys: list[str]) -> str:
        return ""


class TextBulkheadReporter(BulkheadReporter):
    def report(self, registry: BulkheadRegistry, keys: list[str]) -> str:
        if not keys:
            return "bulkhead: no partitions tracked"
        lines = ["bulkhead partitions:"]
        for key in keys:
            active = registry.active_count(key)
            lines.append(f"  {key}: active={active}")
        return "\n".join(lines)


class JsonBulkheadReporter(BulkheadReporter):
    def report(self, registry: BulkheadRegistry, keys: list[str]) -> str:
        data: Dict[str, int] = {key: registry.active_count(key) for key in keys}
        return json.dumps({"bulkhead": data})


def make_bulkhead_reporter(fmt: str) -> BulkheadReporter:
    """Factory that returns a reporter by format name."""
    fmt = fmt.lower().strip()
    if fmt == "json":
        return JsonBulkheadReporter()
    if fmt == "text":
        return TextBulkheadReporter()
    if fmt == "null":
        return NullBulkheadReporter()
    raise ValueError(f"Unknown bulkhead reporter format: '{fmt}'")
