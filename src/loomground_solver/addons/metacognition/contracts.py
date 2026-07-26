"""Read-only observations and governed improvement proposals."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable


class ImprovementKind(str, Enum):
    RULEPACK = "rulepack"
    FILTER = "filter"
    ADAPTER = "adapter"
    TEST = "test"
    FEDERATION_EXAMPLE = "federation_example"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    EVALUATED = "evaluated"
    AUTHORIZED = "authorized"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


class EvaluationPartition(str, Enum):
    TRAINING = "training"
    REGRESSION = "regression"
    ADVERSARIAL = "adversarial"
    HOLDOUT = "holdout"


@dataclass(frozen=True)
class SignedRunRecord:
    run_id: str
    replay_digest: str
    decision: str
    gaps: tuple[str, ...] = field(default_factory=tuple)
    scope_id: str = "default"
    payload: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class RunVerifier(Protocol):
    def verify(self, record: SignedRunRecord) -> bool: ...


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    partition: EvaluationPartition
    input: Mapping[str, Any]
    expected: Mapping[str, Any]


@dataclass(frozen=True)
class EvaluationReport:
    proposal_id: str
    total: int
    passed: int
    partitions: Mapping[str, Mapping[str, int]]
    failures: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    eligible: bool = False


@dataclass(frozen=True)
class ArtifactVersion:
    version_id: str
    proposal_id: str
    artifact_digest: str
    authorization_ref: str
    predecessor: str = ""


@dataclass(frozen=True)
class RollbackRecord:
    rollback_id: str
    from_version: str
    to_version: str
    authorization_ref: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class Observation:
    run_id: str
    replay_digest: str
    decision: str
    gaps: tuple[str, ...] = field(default_factory=tuple)
    downstream_outcome: str | None = None
    scope_id: str = "default"


@dataclass(frozen=True)
class ImprovementProposal:
    proposal_id: str
    kind: ImprovementKind
    motivating_runs: tuple[str, ...]
    proposed_change: Mapping[str, Any]
    status: ProposalStatus = ProposalStatus.DRAFT
    evaluation: Mapping[str, Any] = field(default_factory=dict)
    authorization_ref: str | None = None
    scope_id: str = "default"
    pattern_key: str = ""
