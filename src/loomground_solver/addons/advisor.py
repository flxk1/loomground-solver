# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Deterministic add-on recommendations; never activation or authorization."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

WORLD_MODES = frozenset({"off", "recommend", "required"})
META_MODES = frozenset({"off", "manual", "scheduled"})


@dataclass(frozen=True)
class AdvisorPolicy:
    world_model: str = "off"
    metacognition: str = "off"
    world_threshold: int = 2
    minimum_runs: int = 3

    def __post_init__(self):
        if self.world_model not in WORLD_MODES:
            raise ValueError(f"unknown world-model mode {self.world_model!r}")
        if self.metacognition not in META_MODES:
            raise ValueError(f"unknown metacognition mode {self.metacognition!r}")
        if self.world_threshold < 1 or self.minimum_runs < 1:
            raise ValueError("advisor thresholds must be positive")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "AdvisorPolicy":
        value = value or {}
        world = value.get("world_model", {})
        meta = value.get("metacognition", {})
        return cls(
            world_model=str(world.get("mode", "required" if world.get("enabled") else "off")),
            metacognition=str(meta.get("mode", "manual" if meta.get("enabled") else "off")),
            world_threshold=int(world.get("threshold", 2)),
            minimum_runs=int(meta.get("minimum_runs", 3)),
        )


@dataclass(frozen=True)
class AddonRecommendation:
    addon: str
    mode: str
    eligible: bool
    recommended: bool
    score: int
    threshold: int
    reasons: tuple[str, ...]
    required_inputs: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    expected_benefits: tuple[str, ...]
    risks: tuple[str, ...]
    authorization_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def advise_world_model(problem: Mapping[str, Any], policy: AdvisorPolicy) -> AddonRecommendation:
    reasons = []
    required = {"context_provider"}
    if problem.get("as_of") or problem.get("reference_time"):
        reasons.append("time-sensitive")
        required.add("reference_time")
    if problem.get("requires_current_state"):
        reasons.append("current-state-required")
        required.add("reference_time")
    if problem.get("evidence_refs"):
        reasons.append("external-evidence")
        required.add("evidence_refs")
    if len(problem.get("sources") or ()) > 1:
        reasons.append("multiple-sources")
        required.add("evidence_refs")
    if problem.get("claims_may_conflict"):
        reasons.append("possible-conflict")
        required.add("contradiction-policy")
    if problem.get("freshness_required"):
        reasons.append("freshness-required")
        required.add("reference_time")

    available = set(problem.get("available_inputs") or ())
    if problem.get("evidence_refs"):
        available.add("evidence_refs")
    if problem.get("as_of") or problem.get("reference_time"):
        available.add("reference_time")
    score = len(reasons)
    eligible = policy.world_model != "off" and score >= policy.world_threshold
    recommended = eligible
    if policy.world_model == "off":
        reasons.append("disabled-by-policy")
    missing = tuple(sorted(required - available)) if eligible else ()
    return AddonRecommendation(
        "world_model", policy.world_model, eligible, recommended, score,
        policy.world_threshold, tuple(reasons), tuple(sorted(required)), missing,
        ("immutable-context", "freshness-findings", "context-bound-replay"),
        ("stale-context", "provider-code-execution", "additional-data-handling"),
    )


def advise_metacognition(runs: Iterable[Mapping[str, Any]],
                         policy: AdvisorPolicy) -> AddonRecommendation:
    runs = tuple(runs)
    verified = tuple(run for run in runs if run.get("verified") is True)
    scopes = {str(run.get("scope_id", "default")) for run in verified}
    reasons = []
    if len(verified) >= policy.minimum_runs:
        reasons.append("sufficient-verified-runs")
    else:
        reasons.append("insufficient-verified-runs")
    if len(scopes) > 1:
        reasons.append("mixed-scopes")
    if policy.metacognition == "manual":
        reasons.append("manual-trigger-required")
    if policy.metacognition == "off":
        reasons.append("disabled-by-policy")
    eligible = (policy.metacognition != "off" and
                len(verified) >= policy.minimum_runs and len(scopes) <= 1)
    recommended = eligible and policy.metacognition == "scheduled"
    required = ("verified-run-records", "single-scope", "proposal-reviewer")
    available = set()
    if len(verified) >= policy.minimum_runs:
        available.add("verified-run-records")
    if len(scopes) <= 1:
        available.add("single-scope")
    if any(run.get("proposal_reviewer") for run in runs):
        available.add("proposal-reviewer")
    return AddonRecommendation(
        "metacognition", policy.metacognition, eligible, recommended, len(verified),
        policy.minimum_runs, tuple(reasons), required,
        tuple(sorted(set(required) - available)) if eligible else (),
        ("recurring-gap-detection", "draft-improvement-proposals"),
        ("historical-data-retention", "pattern-overfitting", "review-workload"),
    )


def advise(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Skill-compatible pure function over declared problem/run metadata."""
    policy = AdvisorPolicy.from_mapping(payload.get("policy"))
    recommendations = (
        advise_world_model(payload.get("problem") or {}, policy),
        advise_metacognition(payload.get("runs") or (), policy),
    )
    return {
        "schema": "solver.addon-advice.v1",
        "recommendations": [item.to_dict() for item in recommendations],
        "activation_performed": False,
    }


def skill_manifest() -> dict[str, Any]:
    return {
        "id": "solver.addon-advisor",
        "version": "1",
        "deterministic": True,
        "side_effects": [],
        "input_schema": "solver.addon-advice-request.v1",
        "output_schema": "solver.addon-advice.v1",
    }
