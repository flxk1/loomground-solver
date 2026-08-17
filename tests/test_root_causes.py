# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Root-cause selection over the epistemic-status layer.

The property under test is that this ORDERS the existing fold and re-derives
nothing: `overall` must equal what `propagate_premises` already returned, and the
partition must never turn an open set closed or a closed set open. If root
selection ever starts deciding rather than ordering, these fail.
"""
from __future__ import annotations

from loomground_solver.cross_subsumption import Verdict
from loomground_solver.epistemic_status import (
    EpistemicStatus as E,
    StatusedPremise as S,
    propagate_premises,
    root_causes,
)


def _chain(n: int, root_status: E = E.PRESUPPOSED):
    """One early assumption, then `n` steps each inferred from the last."""
    out = [S("assumption", root_status)]
    for i in range(n):
        out.append(S(f"step-{i}", E.INFERRED,
                     depends_on=((f"step-{i-1}",) if i else ("assumption",))))
    return out


# --- the characteristic case --------------------------------------------------

def test_one_assumption_fifty_consequences_reports_one_root():
    r = root_causes(_chain(50))
    assert r.roots == ("assumption",)
    assert len(r.derived) == 50
    assert r.compression == (1, 51)


def test_compression_does_not_grow_with_chain_length():
    # The whole claim: the causal set is bounded by what is actually unsettled,
    # not by how long the derivation is.
    for n in (10, 100, 500):
        r = root_causes(_chain(n))
        assert len(r.roots) == 1
        assert len(r.derived) == n


def test_a_deep_chain_does_not_exhaust_the_stack():
    r = root_causes(_chain(3000))
    assert r.roots == ("assumption",)
    assert len(r.derived) == 3000


# --- it orders; it does not decide --------------------------------------------

def test_overall_is_the_existing_fold_not_a_second_opinion():
    for premises in (_chain(5), _chain(5, E.ASSERTED), []):
        assert root_causes(premises).overall == propagate_premises(premises).overall


def test_a_fully_settled_set_has_no_roots_and_stays_satisfied():
    r = root_causes(_chain(5, E.ASSERTED))
    assert r.overall is Verdict.SATISFIED
    assert r.roots == ()
    assert r.derived == ()
    assert len(r.settled) == 6


def test_partition_is_total_and_disjoint():
    premises = _chain(20) + [S("loose", E.CONTESTED), S("plain", E.ASSERTED)]
    r = root_causes(premises)
    buckets = list(r.roots) + list(r.derived) + list(r.settled) + list(r.cyclic)
    assert sorted(buckets) == sorted(p.name for p in premises)
    assert len(buckets) == len(set(buckets))


def test_empty_set_folds_vacuously():
    r = root_causes([])
    assert r.roots == () and r.derived == () and r.settled == ()
    assert r.overall is Verdict.SATISFIED


# --- what counts as a root ----------------------------------------------------

def test_every_unsettled_status_is_a_root_on_its_own_merits():
    # Settling something else cannot settle a premise that is itself unsettled.
    for status in (E.PRESUPPOSED, E.CONTESTED, E.UNKNOWN):
        r = root_causes([S("p", status)])
        assert r.roots == ("p",), status


def test_an_unsettled_premise_resting_on_another_is_still_a_root():
    r = root_causes([
        S("a", E.PRESUPPOSED),
        S("b", E.CONTESTED, depends_on=("a",)),
    ])
    assert set(r.roots) == {"a", "b"}
    assert r.derived == ()


def test_several_independent_roots_are_all_reported():
    r = root_causes([
        S("a", E.PRESUPPOSED),
        S("b", E.UNKNOWN),
        S("c", E.INFERRED, depends_on=("a", "b")),
    ])
    assert set(r.roots) == {"a", "b"}
    assert r.derived == ("c",)


def test_openness_is_inherited_transitively():
    r = root_causes([
        S("a", E.PRESUPPOSED),
        S("b", E.INFERRED, depends_on=("a",)),
        S("c", E.INFERRED, depends_on=("b",)),
    ])
    assert r.roots == ("a",)
    assert r.derived == ("b", "c")


def test_a_settled_premise_off_the_open_subgraph_stays_settled():
    r = root_causes([
        S("a", E.PRESUPPOSED),
        S("b", E.INFERRED, depends_on=("a",)),
        S("unrelated", E.ASSERTED),
    ])
    assert r.settled == ("unrelated",)


def test_input_order_is_preserved_within_each_bucket():
    r = root_causes([
        S("z", E.PRESUPPOSED), S("y", E.PRESUPPOSED), S("x", E.PRESUPPOSED)])
    assert r.roots == ("z", "y", "x")


# --- honest edges -------------------------------------------------------------

def test_a_dependency_naming_nothing_is_surfaced_not_dropped():
    r = root_causes([S("a", E.INFERRED, depends_on=("ghost",))])
    assert r.dangling == (("a", "ghost"),)


def test_a_cycle_is_reported_rather_than_resolved():
    r = root_causes([
        S("x", E.INFERRED, depends_on=("y",)),
        S("y", E.INFERRED, depends_on=("x",)),
    ])
    assert set(r.cyclic) == {"x", "y"}
    # No root is invented inside the cycle.
    assert r.roots == ()
    assert r.derived == ()


def test_a_cycle_does_not_hang_the_traversal():
    premises = [S(f"n{i}", E.INFERRED, depends_on=(f"n{(i+1) % 30}",)) for i in range(30)]
    r = root_causes(premises)          # terminates
    assert len(r.cyclic) == 30
