# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Deterministic belief updates and immutable context snapshots.

A minimal take on belief updates and freshness tracking: a belief carries an
explicit freshness window and updates deterministically as new evidence
arrives. Runtime agent state, domain-specific constants, entity resolution,
temporal inference, counterfactual reasoning, and persistence are
intentionally excluded — those stay host-side, outside this package.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .contracts import Belief, ContextSnapshot, Freshness


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def assess_freshness(observed_at: str, reference_at: str, *,
                     current_days: int = 30, stale_days: int = 365) -> Freshness:
    """Classify freshness against an explicit reference time.

    Time is never read implicitly, which keeps snapshots replayable.
    """
    age = (_instant(reference_at) - _instant(observed_at)).days
    if age < current_days:
        return Freshness.CURRENT
    if age < stale_days:
        return Freshness.AGING
    return Freshness.STALE


def update_belief(belief: Belief, *, evidence_ref: str, supports: bool,
                  strength: float = 0.7) -> Belief:
    """Return a new belief after a bounded Bayesian-style evidence update."""
    prior = 0.5 if belief.confidence is None else belief.confidence
    strength = max(0.01, min(0.99, float(strength)))
    likelihood = strength if supports else 1.0 - strength
    contrary = 1.0 - strength if supports else strength
    denominator = likelihood * prior + contrary * (1.0 - prior)
    posterior = prior if denominator == 0 else likelihood * prior / denominator
    posterior = max(0.01, min(0.99, posterior))
    evidence = tuple(dict.fromkeys((*belief.evidence_refs, evidence_ref)))
    supporting = belief.supporting_refs
    contradicting = belief.contradicting_refs
    if supports:
        supporting = tuple(dict.fromkeys((*supporting, evidence_ref)))
    else:
        contradicting = tuple(dict.fromkeys((*contradicting, evidence_ref)))
    return replace(belief, evidence_refs=evidence, confidence=posterior,
                   supporting_refs=supporting, contradicting_refs=contradicting)


def snapshot_digest(*, created_at: str, beliefs: Iterable[Belief],
                    contradictions: Iterable[tuple[str, str]] = ()) -> str:
    body = {
        "created_at": created_at,
        "beliefs": [
            {
                "belief_id": b.belief_id,
                "proposition": dict(b.proposition),
                "evidence_refs": list(b.evidence_refs),
                "observed_at": b.observed_at,
                "freshness": b.freshness.value,
                "confidence": b.confidence,
                "supporting_refs": list(b.supporting_refs),
                "contradicting_refs": list(b.contradicting_refs),
            }
            for b in sorted(beliefs, key=lambda item: item.belief_id)
        ],
        "contradictions": [list(pair) for pair in sorted(contradictions)],
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def make_snapshot(beliefs: Iterable[Belief], *, created_at: str,
                  snapshot_id: str = "",
                  contradictions: Iterable[tuple[str, str]] = ()) -> ContextSnapshot:
    """Canonicalize context and return an immutable, content-addressed snapshot."""
    ordered = tuple(sorted(beliefs, key=lambda item: item.belief_id))
    pairs = tuple(sorted(tuple(sorted(pair)) for pair in contradictions))
    digest = snapshot_digest(created_at=created_at, beliefs=ordered,
                             contradictions=pairs)
    return ContextSnapshot(snapshot_id or digest, created_at, ordered, pairs, digest)


class StaticContextProvider:
    """Simple provider for hosts that already assembled an immutable snapshot."""

    def __init__(self, snapshot: ContextSnapshot):
        self._snapshot = snapshot

    def snapshot(self, request: Mapping[str, Any]) -> ContextSnapshot:
        return self._snapshot


def context_findings(snapshot: ContextSnapshot) -> tuple[dict[str, Any], ...]:
    """Expose stale/unknown and contradictory context for host escalation."""
    findings = [
        {"kind": "context-freshness", "belief_id": belief.belief_id,
         "freshness": belief.freshness.value}
        for belief in snapshot.beliefs
        if belief.freshness in {Freshness.STALE, Freshness.UNKNOWN}
    ]
    findings.extend(
        {"kind": "context-contradiction", "belief_ids": pair}
        for pair in snapshot.contradictions
    )
    return tuple(findings)


def interop_extension(snapshot: ContextSnapshot) -> dict[str, Any]:
    """Project only context identity/findings into ``reasoning.interop``."""
    if not snapshot.digest:
        raise ValueError("context snapshot must have a canonical digest")
    return {
        "snapshot_id": snapshot.snapshot_id,
        "digest": snapshot.digest,
        "created_at": snapshot.created_at,
        "findings": [dict(item) for item in context_findings(snapshot)],
    }
