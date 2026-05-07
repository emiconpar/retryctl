"""Reporters for attempt tagging output."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TextIO

from retryctl.tagging import AttemptTags


class TaggingReporter(ABC):
    @abstractmethod
    def report(self, tags: AttemptTags, stream: TextIO) -> None:
        ...


class NullTaggingReporter(TaggingReporter):
    """No-op reporter; useful when tagging output is not desired."""

    def report(self, tags: AttemptTags, stream: TextIO) -> None:
        pass


class TextTaggingReporter(TaggingReporter):
    """Emits tags as KEY=VALUE lines."""

    def report(self, tags: AttemptTags, stream: TextIO) -> None:
        for key, value in sorted(tags.all().items()):
            stream.write(f"{key}={value}\n")


class JsonTaggingReporter(TaggingReporter):
    """Emits tags as a single JSON object."""

    def report(self, tags: AttemptTags, stream: TextIO) -> None:
        stream.write(json.dumps(tags.all(), sort_keys=True))
        stream.write("\n")
