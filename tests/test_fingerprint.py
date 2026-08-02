# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Pluggable-filter fingerprint: the shipped lenses (logical_form, attack_topology,
negative_space, argument_types, statistics), custom filter registration, the
recall-filter distance over shared facets, and the content signature."""
from __future__ import annotations

import pytest

from loomground_solver import (
    fingerprint, distance, signature, register_filter, FILTERS, FP_VERSION,
    Scenario, Norm, derive, LEX_CONFLICT_PACK, decision_space,
)


def _edge(s, o, dim="causal"):
    return {"id": f"{s}-{o}", "edges": [
        {"subject": s, "predicate": "p", "object": o, "dimension": dim}]}


def test_default_runs_all_registered_filters():
    fp = fingerprint(pairs=[_edge("A", "B", "causal")])
    assert fp["version"] == FP_VERSION
    assert set(fp["facets"]) >= {"logical_form", "attack_topology", "negative_space",
                                 "argument_types", "statistics"}


def test_select_a_subset_of_filters():
    fp = fingerprint(pairs=[_edge("A", "B")], filters=["logical_form", "statistics"])
    assert set(fp["facets"]) == {"logical_form", "statistics"}


# ── shipped filters ──────────────────────────────────────────────────────────

def test_logical_form_filter():
    fp = fingerprint(pairs=[_edge("A", "B", "causal"), _edge("B", "C", "temporal")],
                     norms=[Norm("a", "obligatory", "n1"), Norm("a", "prohibited", "n2")],
                     filters=["logical_form"])
    lf = fp["facets"]["logical_form"]
    assert lf["dimensions"]["causal"] == 1 and lf["dimensions"]["temporal"] == 1
    assert lf["deontic"] == {"obligatory": 1, "permitted": 0, "prohibited": 1}


def test_attack_topology_filter_reinstatement():
    ds = decision_space(["A", "B", "C"], attacks=[("A", "B"), ("B", "C")])
    top = fingerprint(decision=ds, filters=["attack_topology"])["facets"]["attack_topology"]
    assert top["accepted"] == 2 and top["rejected"] == 1 and top["reinstated"] == 1


def test_negative_space_filter():
    case = {"grounds": [{"pinpoint": "X", "exception": "unless the subject objects"}],
            "chain": [{"step": "rule", "warrant": "applies"}], "gaps": ["consent-record"]}
    ns = fingerprint(pack=LEX_CONFLICT_PACK, fired_rules=["lex-specialis"], case=case,
                     filters=["negative_space"])["facets"]["negative_space"]
    assert ns["unfired_defeaters"] == ["lex-posterior", "lex-superior"]
    assert ns["gaps"] == ["consent-record"]
    assert any("unless the subject objects" in x for x in ns["untriggered_exceptions"])


def test_argument_types_filter():
    ds = decision_space(["X", "Y"], attacks=[("X", "Y"), ("Y", "X")])   # conflict
    at = fingerprint(pairs=[_edge("A", "B", "causal"), _edge("B", "C", "intentional")],
                     fired_rules=["lex-superior"], decision=ds,
                     filters=["argument_types"])["facets"]["argument_types"]
    assert at["causal"] == 1 and at["teleological"] == 1
    assert at["hierarchical"] == 1              # from lex-superior
    assert at["conflict"] == 1                  # undecided present


def test_statistics_filter_entropy_and_ratios():
    # two equally-used dimensions -> normalized entropy 1.0; concentration 0.5
    fp = fingerprint(pairs=[_edge("A", "B", "causal"), _edge("C", "D", "temporal")],
                     filters=["statistics"])["facets"]["statistics"]
    assert fp["edges"] == 2 and fp["distinct_dimensions"] == 2
    assert fp["dimension_entropy"] == 1.0 and fp["dimension_concentration"] == 0.5
    # one dimension only -> entropy 0.0, concentration 1.0
    one = fingerprint(pairs=[_edge("A", "B", "causal"), _edge("C", "D", "causal")],
                      filters=["statistics"])["facets"]["statistics"]
    assert one["dimension_entropy"] == 0.0 and one["dimension_concentration"] == 1.0


# ── off_grid: the floor made a first-class facet ─────────────────────────────

def test_off_grid_filter_counts_undeclared_edges():
    # one declared (causal) edge, two off-grid: an unknown label and a missing dimension
    pairs = [
        _edge("A", "B", "causal"),
        {"id": "C-D", "edges": [{"subject": "C", "predicate": "vibes_with",
                                 "object": "D", "dimension": "aesthetic"}]},
        {"id": "E-F", "edges": [{"subject": "E", "predicate": "rhymes_with",
                                 "object": "F"}]},                       # no dimension
    ]
    og = fingerprint(pairs=pairs, filters=["off_grid"])["facets"]["off_grid"]
    assert og["total_edges"] == 3 and og["off_grid_edges"] == 2
    assert og["off_grid_ratio"] == round(2 / 3, 4)
    assert og["off_grid_predicates"] == ["rhymes_with", "vibes_with"]
    assert og["off_grid_dimensions"] == ["aesthetic"]   # missing dim is not a label


def test_off_grid_empty_when_everything_is_on_grid():
    og = fingerprint(pairs=[_edge("A", "B", "causal"), _edge("B", "C", "temporal")],
                     filters=["off_grid"])["facets"]["off_grid"]
    assert og["off_grid_edges"] == 0 and og["off_grid_ratio"] == 0.0
    assert og["off_grid_predicates"] == [] and og["off_grid_dimensions"] == []


def test_off_grid_is_in_the_default_roster():
    fp = fingerprint(pairs=[_edge("A", "B", "causal")])
    assert "off_grid" in fp["facets"]


def test_off_grid_distance_ignores_size_matches_shape():
    # same off-grid predicate set + same ratio at different scales -> distance 0
    small = fingerprint(pairs=[{"id": "1", "edges": [
        {"subject": "a", "predicate": "vibes_with", "object": "b", "dimension": "aesthetic"}]}],
        filters=["off_grid"])
    big = fingerprint(pairs=[
        {"id": "1", "edges": [{"subject": "a", "predicate": "vibes_with",
                               "object": "b", "dimension": "aesthetic"}]},
        {"id": "2", "edges": [{"subject": "c", "predicate": "vibes_with",
                               "object": "d", "dimension": "aesthetic"}]},
    ], filters=["off_grid"])
    assert distance(small, big) == 0.0                  # ratio 1.0 both, same predicate
    # a different off-grid predicate set -> positive, bounded distance
    other = fingerprint(pairs=[{"id": "1", "edges": [
        {"subject": "a", "predicate": "clashes_with", "object": "b", "dimension": "aesthetic"}]}],
        filters=["off_grid"])
    assert 0.0 < distance(small, other) <= 1.0


# ── register a custom filter (the extensibility point) ───────────────────────

def test_register_custom_filter():
    # a toy "statistics-of-content" style filter contributed by a user
    register_filter("edge_count_parity",
                    lambda ctx: {"even": sum(len(p.get("edges", []))
                                             for p in (ctx.get("pairs") or [])) % 2 == 0})
    try:
        fp = fingerprint(pairs=[_edge("A", "B")], filters=["edge_count_parity"])
        assert fp["facets"]["edge_count_parity"] == {"even": False}   # 1 edge -> odd
        # and it participates in distance via the generic comparator
        fp2 = fingerprint(pairs=[_edge("A", "B"), _edge("C", "D")],
                          filters=["edge_count_parity"])
        assert distance(fp, fp2) > 0.0
    finally:
        FILTERS.pop("edge_count_parity", None)


# ── distance + signature ─────────────────────────────────────────────────────

def test_distance_zero_identical_positive_different_and_bounded():
    a = fingerprint(pairs=[_edge("A", "B", "causal")])
    b = fingerprint(pairs=[_edge("A", "B", "causal")])
    c = fingerprint(pairs=[_edge("A", "B", "temporal"), _edge("B", "C", "structural")])
    assert distance(a, b) == 0.0
    assert 0.0 < distance(a, c) <= 1.0
    assert abs(distance(a, c) - distance(c, a)) < 1e-12          # symmetric


def test_distance_only_over_shared_facets_and_weightable():
    a = fingerprint(pairs=[_edge("A", "B", "causal")], filters=["logical_form", "statistics"])
    b = fingerprint(pairs=[_edge("A", "B", "temporal")], filters=["statistics"])
    # only 'statistics' is shared -> distance computed over it alone, no crash
    d = distance(a, b)
    assert 0.0 <= d <= 1.0
    # weighting a facet to 0 removes it
    a2 = fingerprint(pairs=[_edge("A", "B", "causal")], filters=["logical_form", "statistics"])
    b2 = fingerprint(pairs=[_edge("A", "B", "temporal")], filters=["logical_form", "statistics"])
    d_full = distance(a2, b2)
    d_logic_only = distance(a2, b2, weights={"statistics": 0.0})
    assert d_full != d_logic_only


def test_version_mismatch_is_incomparable():
    a = fingerprint(pairs=[_edge("A", "B")])
    b = dict(a); b["version"] = "fp-99"
    with pytest.raises(ValueError):
        distance(a, b)


def test_signature_deterministic_and_content_addressed():
    a = fingerprint(pairs=[_edge("A", "B", "causal")])
    b = fingerprint(pairs=[_edge("A", "B", "causal")])
    c = fingerprint(pairs=[_edge("A", "B", "temporal")])
    assert signature(a) == signature(b) and signature(a).startswith("sha256:")
    assert signature(a) != signature(c)


# ── end-to-end over a real scenario derivation ───────────────────────────────

def test_fingerprint_scenario_across_all_filters():
    sc = Scenario("w", norms=[Norm("act", "obligatory", "general", specificity=0),
                              Norm("act", "prohibited", "specific", specificity=5)],
                  edges=[_edge("cause", "effect", "causal")])
    res = derive(sc, pack=LEX_CONFLICT_PACK)
    fired = [d["rule"] for r in res.acts.values() for d in r.defeats]
    ds = decision_space(["general", "specific"], attacks=[("specific", "general")])
    fp = fingerprint(pairs=sc.edges, norms=sc.norms, pack=LEX_CONFLICT_PACK,
                     fired_rules=fired, decision=ds)
    assert fp["facets"]["logical_form"]["deontic"]["prohibited"] == 1
    assert fp["facets"]["attack_topology"]["accepted"] == 1
    assert "lex-superior" in fp["facets"]["negative_space"]["unfired_defeaters"]
    assert fp["facets"]["argument_types"]["specialization"] == 1     # lex-specialis fired
    assert signature(fp).startswith("sha256:")
