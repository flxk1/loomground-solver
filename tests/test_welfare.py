# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Distributive instrumentation (O149 + O150) — COMPUTE ONLY: what each welfare
principle prescribes, allocation Pareto-efficiency and fair-division checks,
wrapping the existing decide.* and distribution.inequality engines; never a
verdict that a principle is correct."""
from __future__ import annotations

import dataclasses

import pytest

from loomground_solver.welfare import (
    EGALITARIAN,
    PRIORITARIAN,
    RAWLSIAN,
    UTILITARIAN,
    WELFARE_PRINCIPLES,
    FairDivisionReport,
    ParetoReport,
    WelfareEvaluation,
    evaluate,
    fair_division,
    pareto_allocations,
)


# ── O150: welfare-function evaluation — the four principles diverge ──────────

def test_principles_prescribe_different_options():
    # equal=[5,5] sum10 floor5 gini0; skew=[13,1] sum14 floor1;
    # mid=[9,4] sum13 floor4. sqrt-sums: equal=4.472, skew=4.606, mid=5.0.
    ev = evaluate({"equal": [5, 5], "skew": [13, 1], "mid": [9, 4]})
    assert ev.prescriptions[UTILITARIAN] == "skew"    # largest sum (14)
    assert ev.prescriptions[PRIORITARIAN] == "mid"    # largest Σ sqrt(u) (5.0)
    assert ev.prescriptions[RAWLSIAN] == "equal"      # largest floor (5)
    assert ev.prescriptions[EGALITARIAN] == "equal"   # lowest Gini (0)


def test_utilitarian_score_is_the_sum_not_the_mean():
    ev = evaluate({"a": [2, 8], "b": [3, 3]})
    # expected_utility with weight-1 per agent yields the SUM
    assert ev.scores[UTILITARIAN]["a"] == 10.0
    assert ev.scores[UTILITARIAN]["b"] == 6.0
    assert ev.metrics["a"]["total"] == 10.0


def test_rawlsian_is_full_leximin_not_only_the_floor():
    # equal floors (2), so a bare maximin ties; leximin separates on the
    # next-worst coordinate: p's second-worst 8 beats q's 5.
    ev = evaluate({"p": [2, 8], "q": [2, 5]})
    assert ev.prescriptions[RAWLSIAN] == "p"
    assert ev.rankings[RAWLSIAN] == ["p", "q"]
    # the reported score is the floor (from maximin)
    assert ev.scores[RAWLSIAN]["p"] == 2.0
    assert ev.scores[RAWLSIAN]["q"] == 2.0


def test_custom_concave_transform_is_honoured():
    ev = evaluate({"a": [4, 4], "b": [9, 0]}, transform=lambda u: u ** 0.5)
    # sqrt: a=2+2=4.0, b=3+0=3.0 -> prioritarian prefers the even split
    assert ev.prescriptions[PRIORITARIAN] == "a"
    # while utilitarian still prefers the larger raw sum (9 > 8)
    assert ev.prescriptions[UTILITARIAN] == "b"


def test_egalitarian_uses_gini_and_prefers_the_even_split():
    ev = evaluate({"even": [6, 6], "uneven": [11, 1]})
    assert ev.prescriptions[EGALITARIAN] == "even"
    assert ev.scores[EGALITARIAN]["even"] == 0.0
    assert ev.scores[EGALITARIAN]["uneven"] > 0.0


def test_compute_only_boundary_no_winning_principle():
    ev = evaluate({"a": [1, 2], "b": [2, 1]})
    d = ev.to_dict()
    # a prescription per principle, but NO cross-principle verdict
    assert set(d["prescriptions"]) == set(WELFARE_PRINCIPLES)
    for banned in ("correct", "winner", "best", "best_principle", "verdict",
                   "just", "unjust"):
        assert banned not in d
    assert isinstance(ev, WelfareEvaluation)


def test_empty_option_set_is_vacuous():
    ev = evaluate({})
    assert all(ev.prescriptions[p] is None for p in WELFARE_PRINCIPLES)
    assert ev.metrics == {}


# ── O149a: allocation Pareto-efficiency (wraps decide.pareto) ────────────────

def test_pareto_frontier_excludes_dominated_allocations():
    rep = pareto_allocations({"x": [3, 3], "y": [4, 4], "z": [4, 2]})
    # y dominates both x and z (>= on every agent, strictly > on one)
    assert rep.frontier == ("y",)
    assert set(rep.dominated) == {"x", "z"}
    assert rep.on_frontier == {"x": False, "y": True, "z": False}


def test_mutually_nondominated_allocations_are_all_efficient():
    rep = pareto_allocations({"x": [3, 1], "y": [1, 3]})
    assert set(rep.frontier) == {"x", "y"}
    assert rep.dominated == ()
    assert isinstance(rep, ParetoReport)


# ── O149b: fair division (envy-freeness + proportionality) ───────────────────

def test_envy_free_and_proportional_allocation():
    # each agent values its own bundle most and above a 1/n share
    v = {"a": {"a": 10, "b": 4}, "b": {"a": 3, "b": 8}}
    rep = fair_division(v)
    assert rep.envy_free is True
    assert rep.proportional is True
    assert rep.envy_pairs == ()
    assert rep.under_proportional == ()


def test_envy_and_disproportion_are_flagged():
    # agent a values b's bundle (10) above its own (4): envy + below 1/n share
    v = {"a": {"a": 4, "b": 10}, "b": {"a": 3, "b": 8}}
    rep = fair_division(v)
    assert rep.envy_free is False
    assert ("a", "b") in rep.envy_pairs
    assert "a" in rep.envious_agents
    assert rep.proportional is False
    assert "a" in rep.under_proportional
    # a's own value (4) falls below its 1/2 threshold ((4+10)/2 = 7)
    assert rep.shares["a"] == {"own": 4.0, "threshold": 7.0}


def test_fair_division_report_is_frozen_and_measure_only():
    v = {"a": {"a": 5, "b": 5}, "b": {"a": 5, "b": 5}}
    rep = fair_division(v)
    d = rep.to_dict()
    for banned in ("fair", "unfair", "verdict", "just"):
        assert banned not in d
    with pytest.raises(dataclasses.FrozenInstanceError):
        rep.envy_free = False  # type: ignore[misc]
