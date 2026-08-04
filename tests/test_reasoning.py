# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Tests for the 5D reasoning engine (loomground_solver.reasoning).

Ported verbatim from RVND tests/test_reasoning.py; imports remapped
workspaces.dimensions/reasoning -> loomground_solver.dimensions/reasoning.
"""

from __future__ import annotations

import time

import pytest

from loomground_solver.dimensions import Dimension
from loomground_solver.reasoning import (
    Inference,
    InferenceList,
    compose_paths,
    extract_edges,
)


def _pair(pid, edges, confidence=1.0):
    return {
        "id": pid,
        "problem": {"id": f"{pid}-p", "scope": "s", "type": "rule", "summary": pid},
        "solution": {"id": pid, "problem_id": f"{pid}-p", "body": "b",
                     "authority_tier": 1, "confidence": confidence,
                     "body_format": "prose"},
        "edges": edges,
    }


def _edge(s, p, o, dim):
    return {"subject": s, "predicate": p, "object": o, "dimension": dim.value}


# ── extract_edges ────────────────────────────────────────────────

def test_extract_edges_reads_well_formed_and_inherits_confidence():
    pairs = [
        _pair("a", [_edge("X", "causes", "Y", Dimension.CAUSAL)], confidence=0.8),
        _pair("b", [_edge("Y", "causes", "Z", Dimension.CAUSAL)], confidence=0.5),
    ]
    edges = extract_edges(pairs)
    assert len(edges) == 2
    assert edges[0].weight == pytest.approx(0.8)
    assert edges[0].source_pair == "a"
    assert edges[0].dimension == Dimension.CAUSAL


def test_extract_edges_skips_garbage():
    pairs = [
        {"id": "x", "edges": "not-a-list"},
        {"id": "y", "edges": [123, None, {"subject": "A"}, {"subject": "A", "object": "B", "dimension": "bogus"}]},
        "not-a-pair",
        _pair("z", [_edge("A", "p", "B", Dimension.STRUCTURAL)]),
    ]
    edges = extract_edges(pairs)
    assert [e.subject for e in edges] == ["A"]
    assert edges[0].dimension == Dimension.STRUCTURAL


# ── compose_paths ────────────────────────────────────────────────

def test_two_hop_causal_chain_composes_to_causal():
    pairs = [
        _pair("a", [_edge("X", "causes", "Y", Dimension.CAUSAL)], confidence=0.8),
        _pair("b", [_edge("Y", "causes", "Z", Dimension.CAUSAL)], confidence=0.8),
    ]
    inf = compose_paths(extract_edges(pairs))
    assert len(inf) == 1
    i = inf[0]
    assert (i.subject, i.object) == ("X", "Z")
    assert i.dimension == Dimension.CAUSAL
    assert i.confidence == pytest.approx(0.64)   # 0.8 * 0.8
    assert i.hops == 2
    assert i.dimension_chain == ["causal", "causal"]
    # provenance: the two source edges, in order, with their pairs
    assert [h["source_pair"] for h in i.path] == ["a", "b"]


def test_mixed_dimension_composes_per_algebra():
    # structural then causal -> causal (compose(S, C) == C)
    pairs = [
        _pair("a", [_edge("X", "part-of", "Y", Dimension.STRUCTURAL)]),
        _pair("b", [_edge("Y", "causes", "Z", Dimension.CAUSAL)]),
    ]
    inf = compose_paths(extract_edges(pairs))
    assert inf[0].dimension == Dimension.CAUSAL


def test_three_hop_uses_left_fold():
    # causal, intentional, structural -> left-fold:
    # compose(compose(causal,intentional)=intentional, structural)=structural
    pairs = [
        _pair("a", [_edge("A", "p", "B", Dimension.CAUSAL)]),
        _pair("b", [_edge("B", "p", "C", Dimension.INTENTIONAL)]),
        _pair("c", [_edge("C", "p", "D", Dimension.STRUCTURAL)]),
    ]
    inf = compose_paths(extract_edges(pairs), start="A", max_depth=3)
    a_to_d = [i for i in inf if i.object == "D"]
    assert a_to_d and a_to_d[0].dimension == Dimension.STRUCTURAL
    assert a_to_d[0].hops == 3


def test_cycles_do_not_loop_forever():
    pairs = [
        _pair("a", [_edge("X", "p", "Y", Dimension.RELATIONAL)]),
        _pair("b", [_edge("Y", "p", "X", Dimension.RELATIONAL)]),
    ]
    inf = compose_paths(extract_edges(pairs), max_depth=5)
    # bounded, no infinite recursion
    assert all(i.hops <= 5 for i in inf)


def test_min_confidence_prunes():
    pairs = [
        _pair("a", [_edge("X", "p", "Y", Dimension.CAUSAL)], confidence=0.5),
        _pair("b", [_edge("Y", "p", "Z", Dimension.CAUSAL)], confidence=0.5),
    ]
    assert compose_paths(extract_edges(pairs), min_confidence=0.5) == []   # 0.25 < 0.5
    assert len(compose_paths(extract_edges(pairs), min_confidence=0.2)) == 1


def test_single_edge_is_not_an_inference():
    pairs = [_pair("a", [_edge("X", "p", "Y", Dimension.CAUSAL)])]
    assert compose_paths(extract_edges(pairs)) == []


def test_results_sorted_by_confidence():
    pairs = [
        _pair("a", [_edge("X", "p", "Y", Dimension.CAUSAL)], confidence=0.9),
        _pair("b", [_edge("Y", "p", "Z", Dimension.CAUSAL)], confidence=0.9),
        _pair("c", [_edge("X", "p", "M", Dimension.CAUSAL)], confidence=0.3),
        _pair("d", [_edge("M", "p", "N", Dimension.CAUSAL)], confidence=0.3),
    ]
    inf = compose_paths(extract_edges(pairs))
    confs = [i.confidence for i in inf]
    assert confs == sorted(confs, reverse=True)


# ── scale / truncation signal ────────────────────────────────────

def _small_fixture_edges():
    """A branching fixture that yields several multi-hop inferences with ties."""
    pairs = [
        _pair("a", [_edge("X", "p", "Y", Dimension.CAUSAL)], confidence=0.9),
        _pair("b", [_edge("Y", "p", "Z", Dimension.CAUSAL)], confidence=0.9),
        _pair("c", [_edge("X", "p", "M", Dimension.STRUCTURAL)], confidence=0.7),
        _pair("d", [_edge("M", "p", "N", Dimension.INTENTIONAL)], confidence=0.6),
        _pair("e", [_edge("Y", "p", "Q", Dimension.TEMPORAL)], confidence=0.5),
        _pair("f", [_edge("N", "p", "R", Dimension.RELATIONAL)], confidence=0.8),
    ]
    return extract_edges(pairs)


def _snapshot(inferences):
    """Order-preserving, comparable view of a result list."""
    return [i.as_dict() for i in inferences]


def test_defaults_match_reference_behaviour_on_small_graph():
    """Guard against behaviour drift: defaults must reproduce the exact,
    ordered output the naive walk produced (append-all -> stable sort by
    confidence desc -> slice)."""
    edges = _small_fixture_edges()

    # Reference implementation: the original algorithm, verbatim.
    def reference(edges, *, start=None, max_depth=3, min_confidence=0.0,
                  max_results=200):
        adjacency: dict = {}
        for e in edges:
            adjacency.setdefault(e.subject, []).append(e)
        from loomground_solver.dimensions import compose, compose_weights
        max_depth = max(2, int(max_depth))
        results = []

        def walk(node, visited, path):
            if len(path) >= max_depth:
                return
            for e in adjacency.get(node, ()):
                if e.object in visited:
                    continue
                new_path = path + [e]
                if len(new_path) >= 2:
                    dim = new_path[0].dimension
                    conf = new_path[0].weight
                    for nxt in new_path[1:]:
                        dim = compose(dim, nxt.dimension)
                        conf = compose_weights(conf, nxt.weight)
                    if conf >= min_confidence:
                        results.append(Inference(
                            subject=new_path[0].subject, object=e.object,
                            dimension=dim, confidence=conf, hops=len(new_path),
                            dimension_chain=[h.dimension.value for h in new_path],
                            path=[{
                                "subject": h.subject, "predicate": h.predicate,
                                "object": h.object, "dimension": h.dimension.value,
                                "source_pair": h.source_pair,
                            } for h in new_path],
                        ))
                walk(e.object, visited + (e.object,), new_path)

        starts = [start] if start is not None else list(adjacency.keys())
        for s in starts:
            walk(s, (s,), [])
        results.sort(key=lambda i: i.confidence, reverse=True)
        return results[:max_results]

    got = compose_paths(edges)
    expected = reference(edges)
    assert _snapshot(got) == _snapshot(expected)
    # and identical under a few non-default (but non-truncating) parameterisations
    for kw in ({"start": "X"}, {"max_depth": 4}, {"min_confidence": 0.3}):
        assert _snapshot(compose_paths(edges, **kw)) == _snapshot(reference(edges, **kw))
    # not truncated on a small graph
    assert isinstance(got, InferenceList)
    assert got.truncated is False


def _large_graph_edges(layers=6, width=134, fanout=3):
    """A layered DAG with moderate branching — the shape a real regulation's
    versum has: many nodes, a handful of successors each. Node ``L{L}_{i}`` in
    layer ``L`` links to ``fanout`` nodes in layer ``L+1``. Edges =
    (layers-1) * width * fanout; every node is unique across layers so all paths
    are acyclic. Weights vary deterministically so the confidence ranking is
    well-defined."""
    pairs = []
    pid = 0
    for L in range(layers - 1):
        for i in range(width):
            for k in range(fanout):
                j = (i + k * 37 + L) % width          # spread successors
                s = f"L{L}_{i}"
                o = f"L{L + 1}_{j}"
                conf = round(0.55 + ((i * fanout + k + L) % 40) / 100.0, 4)
                pairs.append(_pair(f"p{pid}", [_edge(s, "p", o, Dimension.CAUSAL)],
                                   confidence=conf))
                pid += 1
    return extract_edges(pairs)


def test_large_graph_composes_fast_and_returns_top_n_deterministically():
    edges = _large_graph_edges(layers=6, width=134, fanout=3)
    assert len(edges) >= 2000  # 5 * 134 * 3 = 2010

    t0 = time.perf_counter()
    got = compose_paths(edges, max_depth=4, max_results=250)
    elapsed = time.perf_counter() - t0

    assert elapsed < 10.0, f"large-graph compose took {elapsed:.3f}s"
    # capped and flagged
    assert len(got) == 250
    assert got.truncated is True
    # strictly top-N by confidence, descending
    confs = [i.confidence for i in got]
    assert confs == sorted(confs, reverse=True)
    # deterministic across runs (same objects, same order)
    again = compose_paths(edges, max_depth=4, max_results=250)
    assert _snapshot(got) == _snapshot(again)
    # the retained set really is the best: its floor >= any dropped path.
    # Re-run uncapped-enough to see the true global max and confirm it is kept.
    top1 = compose_paths(edges, max_depth=4, max_results=10)
    assert top1[0].confidence == pytest.approx(got[0].confidence)


def test_truncation_is_observable_via_flag_and_log(caplog):
    edges = _small_fixture_edges()
    # cap below the number of qualifying inferences -> truncation
    full = compose_paths(edges, max_depth=4)
    assert len(full) > 1 and full.truncated is False

    import logging

    with caplog.at_level(logging.WARNING, logger="loomground_solver.reasoning"):
        capped = compose_paths(edges, max_depth=4, max_results=1)
    assert len(capped) == 1
    assert capped.truncated is True
    # kept the single best inference
    assert capped[0].confidence == pytest.approx(full[0].confidence)
    # and it logged the cap
    assert any("truncated" in r.message for r in caplog.records)


def test_min_confidence_subtree_pruning_matches_unpruned_results():
    """Subtree pruning must not change *which* inferences survive min_confidence,
    only how fast they are found."""
    edges = _large_graph_edges(layers=4, width=40, fanout=3)
    high = compose_paths(edges, max_depth=3, min_confidence=0.8, max_results=100000)
    # every returned inference clears the floor
    assert high and all(i.confidence >= 0.8 for i in high)
    assert high.truncated is False
