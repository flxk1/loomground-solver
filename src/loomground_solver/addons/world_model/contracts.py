"""Immutable world-model inputs; no reasoning implementation lives here."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable


class Freshness(str, Enum):
    CURRENT = "current"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Belief:
    belief_id: str
    proposition: Mapping[str, Any]
    evidence_refs: tuple[str, ...]
    observed_at: str
    freshness: Freshness = Freshness.UNKNOWN
    confidence: float | None = None
    supporting_refs: tuple[str, ...] = field(default_factory=tuple)
    contradicting_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.belief_id or not self.observed_at:
            raise ValueError("belief_id and observed_at are required")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "proposition", MappingProxyType(dict(self.proposition)))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "supporting_refs", tuple(self.supporting_refs))
        object.__setattr__(self, "contradicting_refs", tuple(self.contradicting_refs))


@dataclass(frozen=True)
class ContextSnapshot:
    snapshot_id: str
    created_at: str
    beliefs: tuple[Belief, ...] = field(default_factory=tuple)
    contradictions: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    digest: str = ""

    def __post_init__(self):
        object.__setattr__(self, "beliefs", tuple(self.beliefs))
        object.__setattr__(self, "contradictions", tuple(self.contradictions))


@runtime_checkable
class ContextProvider(Protocol):
    def snapshot(self, request: Mapping[str, Any]) -> ContextSnapshot: ...
