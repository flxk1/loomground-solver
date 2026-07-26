from dataclasses import FrozenInstanceError

import pytest

from loomground_solver.addons.world_model import (
    Belief, Freshness, StaticContextProvider, assess_freshness, context_findings, make_snapshot,
    update_belief,
)


def _belief(**kw):
    return Belief("b:1", {"subject": "x", "predicate": "is", "object": "y"},
                  ("e:1",), "2026-01-01T00:00:00Z", **kw)


def test_bayesian_update_is_immutable_and_provenance_bearing():
    original = _belief(confidence=0.5)
    updated = update_belief(original, evidence_ref="e:2", supports=True, strength=0.8)
    assert original.confidence == 0.5
    assert updated.confidence == pytest.approx(0.8)
    assert updated.evidence_refs == ("e:1", "e:2")
    assert updated.supporting_refs == ("e:2",)


def test_freshness_uses_explicit_reference_time():
    assert assess_freshness("2026-01-01T00:00:00Z", "2026-01-20T00:00:00Z") is Freshness.CURRENT
    assert assess_freshness("2026-01-01T00:00:00Z", "2026-06-01T00:00:00Z") is Freshness.AGING
    assert assess_freshness("2025-01-01T00:00:00Z", "2026-06-01T00:00:00Z") is Freshness.STALE


def test_snapshot_is_canonical_content_addressed_and_deeply_read_only():
    a = _belief()
    one = make_snapshot([a], created_at="2026-07-19T00:00:00Z")
    two = make_snapshot([a], created_at="2026-07-19T00:00:00Z")
    assert one == two and one.snapshot_id == one.digest
    with pytest.raises(TypeError):
        one.beliefs[0].proposition["subject"] = "tampered"
    with pytest.raises(FrozenInstanceError):
        one.digest = "tampered"
    assert StaticContextProvider(one).snapshot({}) is one


def test_stale_and_contradictory_context_are_explicit_not_silently_removed():
    stale = _belief(freshness=Freshness.STALE)
    snapshot = make_snapshot([stale], created_at="2026-07-19T00:00:00Z",
                             contradictions=(("b:1", "b:2"),))
    assert snapshot.beliefs[0].freshness is Freshness.STALE
    assert snapshot.contradictions == (("b:1", "b:2"),)
    assert {finding["kind"] for finding in context_findings(snapshot)} == {
        "context-freshness", "context-contradiction"}
