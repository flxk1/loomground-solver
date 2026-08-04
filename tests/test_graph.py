# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Tests for the graph-traversal + graph-prep primitives (loomground_solver.graph).

Covers the neighbourhood sweep (depth, bounding, determinism, empty graph,
dimension filter), the undirected-preparation step (reverse added, dedup,
determinism), and the direct single-hop link via ``compose_paths(min_hops=1)``.
"""

from __future__ import annotations

import pytest

from loomground_solver.dimensions import Dimension
from loomground_solver.graph import neighborhood, to_undirected
from loomground_solver.reasoning import Edge, compose_paths


def _e(s, o, dim=Dimension.RELATIONAL, *, predicate="p", weight=1.0, source_pair=""):
    return Edge(subject=s, predicate=predicate, object=o, dimension=dim,
                weight=weight, source_pair=source_pair)


# ── neighborhood ─────────────────────────────────────────────────

def test_neighborhood_depth_one_is_immediate_ring():
    edges = [_e("A", "B"), _e("B", "C"), _e("C", "D")]
    n = neighborhood(edges, "A", depth=1)
    assert n["focus"] == "A"
    assert n["nodes"] == ["A", "B"]
    assert n["edges"] == [edges[0]]


def test_neighborhood_expands_with_depth():
    edges = [_e("A", "B"), _e("B", "C"), _e("C", "D")]
    assert neighborhood(edges, "A", depth=2)["nodes"] == ["A", "B", "C"]
    assert neighborhood(edges, "A", depth=3)["nodes"] == ["A", "B", "C", "D"]


def test_neighborhood_walks_undirected_for_reach():
    # focus is the OBJECT of an edge; it must still be reached via that edge.
    edges = [_e("X", "A"), _e("A", "Y")]
    n = neighborhood(edges, "A", depth=1)
    assert n["nodes"] == ["A", "X", "Y"]
    assert set(n["edges"]) == set(edges)


def test_neighborhood_bounded_beyond_graph_diameter():
    edges = [_e("A", "B"), _e("B", "C")]
    # depth far beyond the graph yields the whole component, no error, no growth.
    big = neighborhood(edges, "A", depth=99)
    assert big["nodes"] == ["A", "B", "C"]
    assert big["edges"] == edges


def test_neighborhood_depth_zero_is_focus_alone():
    edges = [_e("A", "B")]
    n = neighborhood(edges, "A", depth=0)
    assert n["nodes"] == ["A"]
    assert n["edges"] == []


def test_neighborhood_negative_depth_clamped_to_zero():
    edges = [_e("A", "B")]
    n = neighborhood(edges, "A", depth=-5)
    assert n["nodes"] == ["A"]
    assert n["edges"] == []


def test_neighborhood_empty_graph():
    n = neighborhood([], "A", depth=3)
    assert n == {"focus": "A", "nodes": ["A"], "edges": []}


def test_neighborhood_isolated_focus():
    edges = [_e("B", "C"), _e("C", "D")]
    n = neighborhood(edges, "A", depth=3)
    assert n == {"focus": "A", "nodes": ["A"], "edges": []}


def test_neighborhood_dimension_filter():
    edges = [
        _e("A", "B", Dimension.CAUSAL),
        _e("A", "C", Dimension.STRUCTURAL),
        _e("B", "D", Dimension.CAUSAL),
    ]
    causal = neighborhood(edges, "A", depth=2, dimensions=[Dimension.CAUSAL])
    assert causal["nodes"] == ["A", "B", "D"]
    assert all(e.dimension == Dimension.CAUSAL for e in causal["edges"])
    # string values accepted interchangeably with enum members
    by_str = neighborhood(edges, "A", depth=2, dimensions=["causal"])
    assert by_str["nodes"] == causal["nodes"]


def test_neighborhood_empty_dimension_filter_excludes_everything():
    edges = [_e("A", "B", Dimension.CAUSAL)]
    n = neighborhood(edges, "A", depth=2, dimensions=[])
    assert n["nodes"] == ["A"]
    assert n["edges"] == []


def test_neighborhood_dedupes_and_is_deterministic():
    dup = _e("A", "B")
    edges = [dup, dup, _e("B", "C")]
    n = neighborhood(edges, "A", depth=2)
    # the duplicate edge is selected at most once
    assert n["edges"].count(dup) == 1
    # deterministic across runs
    again = neighborhood(edges, "A", depth=2)
    assert n == again
    # nodes are sorted
    assert n["nodes"] == sorted(n["nodes"])


# ── to_undirected ────────────────────────────────────────────────

def test_to_undirected_adds_reverse():
    edges = [_e("A", "B", Dimension.CAUSAL, weight=0.7, source_pair="pp")]
    out = to_undirected(edges)
    assert len(out) == 2
    fwd, rev = out
    assert (fwd.subject, fwd.object) == ("A", "B")
    assert (rev.subject, rev.object) == ("B", "A")
    # reverse carries dimension / weight / provenance unchanged
    assert rev.dimension == Dimension.CAUSAL
    assert rev.weight == pytest.approx(0.7)
    assert rev.source_pair == "pp"
    assert rev.predicate == "p"


def test_to_undirected_dedups_existing_reverse():
    # graph already contains both directions -> no duplicates added
    edges = [_e("A", "B"), _e("B", "A")]
    out = to_undirected(edges)
    assert out == edges


def test_to_undirected_dedups_duplicate_inputs():
    dup = _e("A", "B")
    out = to_undirected([dup, dup])
    # one forward + one reverse, duplicates collapsed
    assert len(out) == 2
    assert {(e.subject, e.object) for e in out} == {("A", "B"), ("B", "A")}


def test_to_undirected_self_loop_not_doubled():
    loop = _e("A", "A")
    out = to_undirected([loop])
    assert out == [loop]


def test_to_undirected_deterministic_order():
    edges = [_e("A", "B"), _e("B", "C")]
    out = to_undirected(edges)
    # originals first (input order), then reverses (input order)
    assert [(e.subject, e.object) for e in out] == [
        ("A", "B"), ("B", "C"), ("B", "A"), ("C", "B"),
    ]
    assert to_undirected(edges) == out


def test_to_undirected_enables_reverse_traversal():
    # directed A->B->C only; a walk from C reaches nothing without prep.
    edges = [_e("A", "B", Dimension.CAUSAL), _e("B", "C", Dimension.CAUSAL)]
    forward_only = [i for i in compose_paths(edges, start="C") if i.object == "A"]
    assert forward_only == []
    undirected = to_undirected(edges)
    reachable = [i for i in compose_paths(undirected, start="C") if i.object == "A"]
    assert reachable and reachable[0].hops == 2


def test_to_undirected_empty():
    assert to_undirected([]) == []


# ── direct single-hop link via compose_paths(min_hops=1) ─────────

def test_min_hops_one_records_direct_edge():
    edges = [_e("A", "B", Dimension.CAUSAL, weight=0.8)]
    # default (min_hops=2): a single edge is a fact, not an inference
    assert compose_paths(edges) == []
    # min_hops=1: the direct edge is a 1-hop inference
    direct = compose_paths(edges, start="A", min_hops=1)
    assert len(direct) == 1
    i = direct[0]
    assert (i.subject, i.object, i.hops) == ("A", "B", 1)
    assert i.dimension == Dimension.CAUSAL
    assert i.confidence == pytest.approx(0.8)
    assert i.dimension_chain == ["causal"]


def test_min_hops_one_direct_then_composed_in_one_call():
    # a direct A->C and a longer A->B->C both exist; one call yields both.
    edges = [
        _e("A", "C", Dimension.RELATIONAL, weight=0.9),
        _e("A", "B", Dimension.RELATIONAL, weight=0.9),
        _e("B", "C", Dimension.RELATIONAL, weight=0.9),
    ]
    to_c = [i for i in compose_paths(edges, start="A", min_hops=1) if i.object == "C"]
    hops = sorted(i.hops for i in to_c)
    assert hops == [1, 2]
    # best-confidence first -> the direct 1-hop (0.9) outranks the 2-hop (0.81)
    first_to_c = next(i for i in compose_paths(edges, start="A", min_hops=1)
                      if i.object == "C")
    assert first_to_c.hops == 1


def test_min_hops_clamped_to_at_least_one():
    edges = [_e("A", "B")]
    # min_hops=0 behaves like min_hops=1 (no zero-hop "paths")
    assert len(compose_paths(edges, start="A", min_hops=0)) == 1


def test_min_hops_default_matches_two():
    edges = [_e("A", "B"), _e("B", "C")]
    assert compose_paths(edges) == compose_paths(edges, min_hops=2)


def test_min_hops_three_reports_only_longer_chains():
    edges = [_e("A", "B"), _e("B", "C"), _e("C", "D")]
    long_only = compose_paths(edges, start="A", max_depth=3, min_hops=3)
    assert [i.hops for i in long_only] == [3]
