# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Rung-4 scenario tests: reasoning inside a world, defeasible normative
resolution, possible-worlds divergence, and projection into the contract."""
from __future__ import annotations

from loomground_solver import (
    Scenario, Norm, derive, compare, to_case, check,
    GENERIC_PACK, LEX_CONFLICT_PACK,
)


def _edge(s, p, o, dim="causal"):
    return {"id": f"{s}-{o}", "edges": [
        {"subject": s, "predicate": p, "object": o, "dimension": dim}]}


# ── epistemic closure inside a world ─────────────────────────────────────────

def test_scenario_composes_multi_hop_inference():
    sc = Scenario("w1", edges=[_edge("A", "causes", "B"), _edge("B", "causes", "C")])
    res = derive(sc)
    assert any(i.subject == "A" and i.object == "C" for i in res.inferences)


# ── defeasible normative resolution ──────────────────────────────────────────

def test_generic_pack_escalates_a_genuine_collision():
    # two contradictory norms on the same act, no ordering to separate them
    sc = Scenario("w", norms=[
        Norm("share-data", "obligatory", source="n1"),
        Norm("share-data", "prohibited", source="n2"),
    ])
    r = derive(sc, pack=GENERIC_PACK).resolution_for("share-data")
    assert r.status == "open" and r.verdict is None
    assert ("n1", "n2") in [tuple(sorted(c)) for c in r.collisions]


def test_lex_specialis_defeats_the_general_norm():
    # same collision, but n2 is more specific -> lex specialis resolves it
    sc = Scenario("w", norms=[
        Norm("share-data", "obligatory", source="general", specificity=0),
        Norm("share-data", "prohibited", source="specific", specificity=5),
    ])
    r = derive(sc, pack=LEX_CONFLICT_PACK).resolution_for("share-data")
    assert r.status == "determinate" and r.verdict == "prohibited"
    assert {"loser": "general", "winner": "specific", "rule": "lex-specialis"} in r.defeats


def test_lex_superior_beats_lex_specialis_in_priority():
    # higher rank wins even though the other is more specific (ordering priority)
    sc = Scenario("w", norms=[
        Norm("act", "obligatory", source="constitution", rank=9, specificity=0),
        Norm("act", "prohibited", source="bylaw", rank=1, specificity=9),
    ])
    r = derive(sc, pack=LEX_CONFLICT_PACK).resolution_for("act")
    assert r.verdict == "obligatory"
    assert r.defeats[0]["rule"] == "lex-superior"


def test_reinstatement_a_defeated_defeater_frees_its_target():
    # Z permits (rank 3), Y prohibits (rank 2), X obligates (rank 1).
    # Z⇔Y and Y⇔X contradict; Z⇔X do not. Naive pairwise defeat would drop X
    # (Y "beats" X) and wrongly answer permitted. Grounded: Z IN → Y OUT → X
    # reinstated (its only attacker Y is OUT) → survivors {Z, X} → obligatory.
    sc = Scenario("w", norms=[
        Norm("act", "permitted", source="Z", rank=3),
        Norm("act", "prohibited", source="Y", rank=2),
        Norm("act", "obligatory", source="X", rank=1),
    ])
    r = derive(sc, pack=LEX_CONFLICT_PACK).resolution_for("act")
    assert r.status == "determinate" and r.verdict == "obligatory"
    assert set(r.survivors) == {"Z", "X"}
    # the misleading "Y defeats X" is NOT recorded, because Y ends up defeated
    assert not any(d["loser"] == "X" for d in r.defeats)


def test_odd_cycle_of_genuine_collisions_escalates():
    # three mutually-contradictory norms the generic pack cannot separate:
    # none can be IN → all undecided → collision → escalate, never a guess.
    sc = Scenario("w", norms=[
        Norm("act", "obligatory", source="a"),
        Norm("act", "prohibited", source="b"),
        Norm("act", "prohibited", source="c"),
    ])
    r = derive(sc, pack=GENERIC_PACK).resolution_for("act")
    assert r.status == "open" and r.verdict is None and r.collisions


def test_noncontradictory_norms_are_determinate():
    sc = Scenario("w", norms=[
        Norm("act", "permitted", source="a"),
        Norm("act", "obligatory", source="b"),   # obligatory implies permitted, no clash
    ])
    r = derive(sc).resolution_for("act")
    assert r.status == "determinate" and r.verdict == "obligatory"


# ── possible worlds: same act, different answer ──────────────────────────────

def test_possible_worlds_diverge():
    w1 = Scenario("permits", norms=[Norm("x", "permitted", source="p")])
    w2 = Scenario("forbids", norms=[Norm("x", "prohibited", source="f")])
    verdicts = compare([w1, w2], "x")
    assert verdicts["permits"] == ("determinate", "permitted")
    assert verdicts["forbids"] == ("determinate", "prohibited")


# ── projection into the reasoning contract ───────────────────────────────────

def test_determinate_scenario_projects_to_a_clean_contract_case():
    sc = Scenario("w", norms=[
        Norm("act", "obligatory", source="general", specificity=0),
        Norm("act", "prohibited", source="specific", specificity=5),
    ])
    res = derive(sc, pack=LEX_CONFLICT_PACK)
    case = to_case(res, "act")
    rep = check(case)                       # runs the reasoning contract
    assert not rep.violations               # determinate + warranted defeater step => no violation


def test_collision_scenario_projects_to_an_open_case_that_escalates():
    sc = Scenario("w", norms=[
        Norm("act", "obligatory", source="n1"),
        Norm("act", "prohibited", source="n2"),
    ])
    res = derive(sc, pack=GENERIC_PACK)
    case = to_case(res, "act")
    rep = check(case, stake=True)           # a stakeful open case
    # residual with no recorded choice => the contract flags it for a human
    assert any(f.code in ("RC-3", "RC-4") and f.level.value == "escalate"
               for f in rep.findings)
