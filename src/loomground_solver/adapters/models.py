"""Immutable Solver-native records emitted by universal system adapters."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..dimensions import Dimension

_DIMENSIONS = frozenset(d.value for d in Dimension)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: str, limit: int = 256) -> None:
    if not value or len(value) > limit:
        raise ValueError(f"{name} must contain 1..{limit} characters")


@dataclass(frozen=True)
class SystemIdentity:
    system_id: str
    version: str
    artifact_sha256: str
    adapter_id: str
    adapter_version: str

    def __post_init__(self) -> None:
        for name in ("system_id", "version", "adapter_id", "adapter_version"):
            _required(name, getattr(self, name))
        if not _SHA256.fullmatch(self.artifact_sha256):
            raise ValueError("artifact_sha256 must be 64 lowercase hexadecimal characters")


@dataclass(frozen=True)
class AdapterCapabilities:
    artifacts: bool = False
    parsing: bool = False
    semantic_projection: bool = False
    evaluation: bool = False
    export: bool = False


@dataclass(frozen=True)
class NDSystem:
    system_id: str
    namespace: str
    version: str
    axes: Mapping[str, Mapping[str, Any]]

    def __post_init__(self) -> None:
        for name in ("system_id", "namespace", "version"):
            _required(name, getattr(self, name))
        if not self.axes:
            raise ValueError("nD system requires at least one axis")


@dataclass(frozen=True)
class CoordinateAssignment:
    assignment_id: str
    subject_id: str
    system_id: str
    system_version: str
    axis_id: str
    value: Any
    source_id: str
    method: str
    verification: str = "attested"

    def __post_init__(self) -> None:
        for name in ("assignment_id", "subject_id", "system_id", "system_version",
                     "axis_id", "source_id", "method", "verification"):
            _required(name, getattr(self, name))


@dataclass(frozen=True)
class SolverProjection:
    """Adapter output consumable by existing entailment and fingerprint APIs."""

    identity: SystemIdentity
    pairs: tuple[Mapping[str, Any], ...] = ()
    nd_systems: tuple[NDSystem, ...] = ()
    assignments: tuple[CoordinateAssignment, ...] = ()
    observation: Mapping[str, Any] = field(default_factory=dict)

    def validate(self, *, max_items: int = 100_000) -> "SolverProjection":
        edge_count = sum(len(pair.get("edges", ())) for pair in self.pairs)
        if edge_count + len(self.assignments) > max_items:
            raise ValueError(f"projection exceeds item limit {max_items}")
        for pair in self.pairs:
            _required("pair id", str(pair.get("id", "")))
            for edge in pair.get("edges", ()):
                if not all(str(edge.get(k, "")).strip()
                           for k in ("subject", "predicate", "object")):
                    raise ValueError("projected edge needs subject, predicate, and object")
                if edge.get("dimension") not in _DIMENSIONS:
                    raise ValueError(f"unknown edge dimension: {edge.get('dimension')!r}")
        systems = {(system.system_id, system.version): system for system in self.nd_systems}
        for assignment in self.assignments:
            system = systems.get((assignment.system_id, assignment.system_version))
            if system is None:
                raise ValueError(f"assignment {assignment.assignment_id!r} names unknown system")
            if assignment.axis_id not in system.axes:
                raise ValueError(f"assignment {assignment.assignment_id!r} names unknown axis")
        return self

    def fingerprint_context(self) -> dict[str, Any]:
        """Return the existing fingerprint input plus lossless typed nD coordinates."""
        return {
            "pairs": list(self.pairs),
            "adapter_coordinates": [
                {"system": a.system_id, "version": a.system_version,
                 "axis": a.axis_id, "value": a.value, "subject": a.subject_id}
                for a in self.assignments
            ],
        }
