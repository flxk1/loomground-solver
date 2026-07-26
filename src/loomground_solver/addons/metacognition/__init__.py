"""Observation and proposal contracts for Solver metacognition."""

from .contracts import (ArtifactVersion, EvaluationCase, EvaluationPartition,
                        EvaluationReport, ImprovementKind, ImprovementProposal,
                        Observation, ProposalStatus, RollbackRecord, RunVerifier,
                        SignedRunRecord)
from .evaluation import evaluate_proposal
from .lifecycle import JsonlVersionRegistry, authorize, promote, rollback
from .observer import observe, observe_record, recurring_gap_proposals, signals
from .store import JsonlProposalStore

__all__ = ["ArtifactVersion", "EvaluationCase", "EvaluationPartition",
           "EvaluationReport", "ImprovementKind", "ImprovementProposal",
           "Observation", "ProposalStatus", "RollbackRecord", "RunVerifier",
           "SignedRunRecord", "JsonlProposalStore", "JsonlVersionRegistry",
           "authorize", "evaluate_proposal", "observe", "observe_record",
           "promote", "recurring_gap_proposals", "rollback", "signals"]
