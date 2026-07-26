from __future__ import annotations

import pytest

from loomground_solver import (
    AdapterRegistry, LoomgroundAdapter, SystemAdapter, SystemIdentity, adapt_loomground,
    compose_paths, extract_edges, fingerprint,
)
from loomground_solver.adapters.loomground import RELATIONS
from loomground_solver.adapters.models import CoordinateAssignment, NDSystem, SolverProjection


SOURCE = """\
actor app party acme grade L3
gate review risk high grade L2 grant app
gate publish
cord review -> publish
cord publish -> master
reserve export by steward duration 7d : halt
"""


def test_loomground_is_immediate_5d_nd_capability():
    projection = adapt_loomground(SOURCE)
    edges = projection.pairs[0]["edges"]
    assert {(edge["predicate"], edge["dimension"]) for edge in edges} >= {
        ("authority", "intentional"),
        ("pipe", "causal"),
        ("egress", "causal"),
        ("reservation", "intentional"),
    }
    coordinates = {(a.subject_id, a.axis_id, a.value) for a in projection.assignments}
    assert ("app", "party", "acme") in coordinates
    assert ("app", "grade", "L3") in coordinates
    assert ("review", "risk", "high") in coordinates
    assert any(axis == "duration" and value == "7d"
               for _subject, axis, value in coordinates)


def test_loomground_mapping_matches_the_ecosystem_reference_semantics():
    assert RELATIONS == {
        "authority": ("intentional", "authorizes"),
        "pipe": ("causal", "activates"),
        "egress": ("causal", "releases_to"),
        "on_behalf_of": ("relational", "delegates_for"),
        "reservation": ("intentional", "reserves_for"),
        "redress": ("intentional", "remedy_by"),
    }
    assert isinstance(LoomgroundAdapter(), SystemAdapter)


def test_projection_feeds_existing_reasoning_and_fingerprint():
    projection = adapt_loomground(SOURCE)
    edges = extract_edges(projection.pairs)
    inferences = compose_paths(edges, start="app", max_depth=4)
    assert any(inference.object == "master" for inference in inferences)
    fp = fingerprint(**projection.fingerprint_context())
    assert fp["facets"]["logical_form"]["dimensions"]["causal"] == 2
    assert fp["facets"]["logical_form"]["dimensions"]["intentional"] == 2


def test_adapter_preserves_local_predicates_and_semantic_roles():
    projection = LoomgroundAdapter().project(SOURCE)
    authority = next(edge for edge in projection.pairs[0]["edges"]
                     if edge["predicate"] == "authority")
    assert authority["semantic_role"] == "authorizes"
    assert authority["attributes"]["type"] == "authority"


def test_unknown_semantics_fail_closed():
    observation = {
        "nodes": [{"id": "a", "class": "actor"}, {"id": "b", "class": "gate"}],
        "cords": [{"from": "a", "to": "b", "type": "guessed"}],
        "reservations": [],
    }
    with pytest.raises(ValueError, match="no Federation-5D mapping"):
        adapt_loomground(observation)


class _Adapter:
    def __init__(self, identity):
        self._identity = identity

    def identity(self):
        return self._identity


def test_adapter_registry_is_collision_safe():
    first = SystemIdentity("example", "1", "a" * 64, "example.adapter", "1")
    registry = AdapterRegistry([_Adapter(first)])
    assert registry.for_system("example").identity() == first
    with pytest.raises(ValueError, match="conflicting adapter"):
        registry.register(_Adapter(SystemIdentity(
            "example", "2", "b" * 64, "other.adapter", "1")))


def test_projection_rejects_unknown_coordinate_system_and_axis():
    identity = SystemIdentity("example", "1", "a" * 64, "example.adapter", "1")
    system = NDSystem("context", "example", "1", {"risk": {"type": "ordered"}})
    unknown_system = CoordinateAssignment(
        "a1", "subject", "missing", "1", "risk", "high", "urn:test", "test")
    with pytest.raises(ValueError, match="unknown system"):
        SolverProjection(identity, nd_systems=(system,),
                         assignments=(unknown_system,)).validate()
    unknown_axis = CoordinateAssignment(
        "a2", "subject", "context", "1", "grade", "L2", "urn:test", "test")
    with pytest.raises(ValueError, match="unknown axis"):
        SolverProjection(identity, nd_systems=(system,),
                         assignments=(unknown_axis,)).validate()


def test_adapter_context_is_absent_for_legacy_fingerprints():
    legacy = fingerprint(pairs=[])
    assert legacy["facets"]["adapter_context"] is None
    projected = fingerprint(**adapt_loomground(SOURCE).fingerprint_context())
    assert projected["facets"]["adapter_context"]
