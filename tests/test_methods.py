# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The open reasoning-methods registry: logic, philosophy, methodology,
rationalist decision theory, mathematics, data science."""
from __future__ import annotations

from loomground_solver import METHODS, method, methods_by_kind, register_method, Rule


def test_registry_is_populated_across_kinds():
    assert set(methods_by_kind("inference")) >= {
        "modus_ponens", "modus_tollens", "hypothetical_syllogism",
        "disjunctive_syllogism", "abduction", "analogical_inference",
        "inductive_generalization"}
    assert set(methods_by_kind("decision")) >= {
        "maximin", "maximax", "hurwicz", "minimax_regret", "expected_utility",
        "bayesian_update", "pareto", "lexicographic", "satisficing"}
    assert set(methods_by_kind("test")) >= {"falsification", "consistency",
                                            "hypothetico_deductive"}


# ── logic ────────────────────────────────────────────────────────────────────

def test_modus_ponens_and_tollens():
    rules = [Rule("r", ("P",), "Q")]
    assert "Q" in method("modus_ponens")({"P"}, rules)["facts"]
    assert "-P" in method("modus_tollens")({"-Q"}, rules)["facts"]


def test_hypothetical_and_disjunctive_syllogism():
    hs = method("hypothetical_syllogism")(set(), [Rule("a", ("P",), "Q"), Rule("b", ("Q",), "R")])
    assert any(r.conditions == ("P",) and r.consequence == "R" for r in hs["rules"])
    ds = method("disjunctive_syllogism")({"a|b", "-a"})
    assert "b" in ds["facts"]


# ── philosophy ───────────────────────────────────────────────────────────────

def test_abduction_proposes_the_parsimonious_explanation():
    # observe Q; rule P->Q; P unknown  =>  candidate explanation ?P
    out = method("abduction")({"Q"}, [Rule("r", ("P",), "Q")])
    assert "?P" in out["facts"]


def test_analogical_inference_transfers_structure():
    out = method("analogical_inference")(
        set(), mapping={"sun": "nucleus", "planet": "electron"},
        source_relations=[("planet", "orbits", "sun")])
    assert "electron:orbits:nucleus" in out["facts"]


# ── data science ─────────────────────────────────────────────────────────────

def test_inductive_generalization_confidence():
    obs = [{"x": 1, "p": True, "q": True}, {"x": 2, "p": True, "q": True},
           {"x": 3, "p": True, "q": False}]
    out = method("inductive_generalization")(obs)
    assert out["support"] == 3 and out["confidence"] == round(2 / 3, 6)
    assert out["rules"]


def test_bayesian_update_posterior_and_map():
    out = method("bayesian_update")(
        prior={"h1": 0.5, "h2": 0.5},
        likelihoods={"h1": {"e": 0.9}, "h2": {"e": 0.2}}, evidence="e")
    assert out["choice"] == "h1"                              # MAP
    assert abs(out["scores"]["h1"] - 0.45 / 0.55) < 1e-6


# ── rationalist decision theory ──────────────────────────────────────────────

_PAYOFFS = {"A": {"s1": 10, "s2": 2}, "B": {"s1": 6, "s2": 6}, "C": {"s1": 8, "s2": 4}}


def test_decision_rules_under_uncertainty():
    assert method("maximin")(payoffs=_PAYOFFS)["choice"] == "B"       # best worst-case
    assert method("maximax")(payoffs=_PAYOFFS)["choice"] == "A"       # best best-case
    assert method("minimax_regret")(payoffs=_PAYOFFS)["choice"] == "C"  # least max-regret


def test_expected_utility_under_risk():
    eu = method("expected_utility")(payoffs=_PAYOFFS,
                                    probabilities={"s1": 0.8, "s2": 0.2})
    assert eu["choice"] == "A" and eu["scores"]["A"] == 8.4


# ── mathematics ──────────────────────────────────────────────────────────────

def test_pareto_frontier_and_lexicographic():
    par = method("pareto")(vectors={"A": [2, 1], "B": [1, 2], "C": [1, 1]})
    assert set(par["ranking"][:2]) == {"A", "B"} and par["scores"]["C"] == 0.0  # C dominated
    lex = method("lexicographic")(vectors={"A": [1, 5], "B": [1, 9], "C": [2, 0]})
    assert lex["ranking"] == ["C", "B", "A"]


def test_satisficing_takes_the_first_good_enough():
    out = method("satisficing")(options=["A", "B", "C"],
                                valuations={"A": 0.3, "B": 0.7, "C": 0.9}, aspiration=0.6)
    assert out["choice"] == "B"


# ── methodology / test ───────────────────────────────────────────────────────

def test_falsification_and_consistency():
    f = method("falsification")({"P", "-Q"}, [Rule("r", ("P",), "Q")])
    assert f["any_falsified"] and "r" in f["falsified"]
    assert method("consistency")({"x", "-x"})["consistent"] is False
    assert method("consistency")({"x", "y"})["consistent"] is True


# ── extensibility ────────────────────────────────────────────────────────────

def test_register_a_custom_method():
    register_method("always_A", "decision", lambda **kw: {"choice": "A", "ranking": ["A"], "scores": {}})
    try:
        assert method("always_A")()["choice"] == "A"
        assert "always_A" in methods_by_kind("decision")
    finally:
        METHODS.pop("always_A", None)
