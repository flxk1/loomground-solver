"""Read-only observations and governed improvement proposals."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import Enum, EnumMeta
from typing import Any, Mapping, Protocol, runtime_checkable

_FEDERATION_EXAMPLE_DEPRECATION = (
    "ImprovementKind.FEDERATION_EXAMPLE (and the 'federation_example' value) "
    "is deprecated and will be removed in a future release; use "
    "ImprovementKind.CORPUS_EXAMPLE ('corpus_example') instead."
)


class _ImprovementKindMeta(EnumMeta):
    """Compatible with 3.10 and 3.12: EnumMeta's own ``__getattr__`` only
    resolves live member names, so the retired ``FEDERATION_EXAMPLE`` alias is
    hooked in here rather than as a class attribute (which would create a
    second, divergent member)."""

    def __getattr__(cls, name: str):
        if name == "FEDERATION_EXAMPLE":
            warnings.warn(_FEDERATION_EXAMPLE_DEPRECATION, DeprecationWarning, stacklevel=2)
            return cls.CORPUS_EXAMPLE
        return super().__getattr__(name)


class ImprovementKind(str, Enum, metaclass=_ImprovementKindMeta):
    RULEPACK = "rulepack"
    FILTER = "filter"
    ADAPTER = "adapter"
    TEST = "test"
    CORPUS_EXAMPLE = "corpus_example"

    @classmethod
    def _missing_(cls, value):
        if value == "federation_example":
            warnings.warn(_FEDERATION_EXAMPLE_DEPRECATION, DeprecationWarning, stacklevel=3)
            return cls.CORPUS_EXAMPLE
        return None


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
