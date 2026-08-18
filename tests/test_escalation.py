# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Escalation: autonomy as the lowest ceiling, not a weighted sum.

Three properties are defended, and each is a place a scored formula goes wrong.
Nothing compensates for anything. The factor doing the capping can always be
named. A factor nobody assessed caps at the floor rather than dropping out of the
minimum — the difference between a conservative calculus and a decorative one.

The fourth is the direction of travel: the calculus lowers autonomy on its own and
never raises it, because an escalation follows from the state of the world while a
restoration is an act someone is answerable for.

The fifth is a boundary. **The ladder is the caller's.** The governance language
already owns it and publishes it as remappable data; a copy here would be a
divergent second one in the layer that holds no deployments. The ladder used below
is test data in a host's shape, not something this package ships, and one test
proves the package ships none.
"""
from __future__ import annotations

from itertools import product

import pytest

from loomground_solver.cross_subsumption import Verdict
from loomground_solver.escalation import (
    Escalation, Factor as F, Ladder,
    autonomy_verdict, ceiling, fold_autonomy, relax,
)

# A host's ladder, standing in for one read from governance's `vocabulary/grades.json`.
GRADES = Ladder(("L0", "L1", "L2", "L3", "L4"))
FLOOR = GRADES.floor
TOP = GRADES.top

# The caller's factor vocabulary, likewise test data only.
FIVE = ("risk", "uncertainty", "reversibility", "context", "competence")


def _all(level):
    return [F(n, level) for n in FIVE]


def _ceiling(factors, delegated=TOP, ladder=GRADES):
    return ceiling(factors, delegated=delegated, ladder=ladder)


# --- the ladder belongs to the caller ----------------------------------------------

def test_the_package_ships_no_ladder():
    # The governance language owns this ladder and publishes it as remappable
    # data. A second one here would be a divergent copy in the layer that holds
    # no deployments — and it would be reachable as a default, which is how such
    # copies come to be relied on.
    import inspect

    from loomground_solver import escalation as mod
    src = inspect.getsource(mod)
    for forbidden in (*GRADES.levels, "SUSPENDED", "PROPOSE", "CONFIRM", "NOTIFY", "ACT"):
        assert forbidden not in src, f"{forbidden} looks like a shipped level"
    assert "Ladder(" not in src.split('"""', 2)[2], "a ladder is constructed here"


def test_a_ladder_with_other_names_and_another_arity_works_identically():
    # The kernel compares positions and reads no name.
    three = Ladder(("stop", "ask", "go"))
    out = ceiling([F("risk", "ask")], delegated="go", ladder=three)
    assert out.granted == "ask" and out.binding == ("risk",)


def test_a_level_off_the_ladder_is_refused_not_coerced():
    # Reading an unknown level as the floor would turn a wiring mistake into a
    # policy, and a conservative-looking one, which is how it would survive.
    with pytest.raises(ValueError, match="not on this ladder"):
        _ceiling([F("risk", "L9")])
    with pytest.raises(ValueError, match="not on this ladder"):
        _ceiling([], delegated="L9")


def test_a_ladder_must_be_ordered_and_distinct():
    with pytest.raises(ValueError):
        Ladder(())
    with pytest.raises(ValueError):
        Ladder(("L0", "L1", "L0"))


def test_the_floor_is_the_ladders_own_first_rung():
    two = Ladder(("halt", "run"))
    assert ceiling([F("risk")], delegated="run", ladder=two).granted == "halt"


# --- the lowest ceiling wins ------------------------------------------------------

def test_the_lowest_ceiling_is_what_is_granted():
    fs = _all(TOP)
    fs[2] = F("reversibility", "L2")
    assert _ceiling(fs).granted == "L2"


def test_no_factor_compensates_for_another():
    # The trap. Under a weighted sum, four factors at the top could outweigh one
    # at the bottom. Competence does not make an irreversible act reversible.
    fs = _all(TOP)
    fs[2] = F("reversibility", FLOOR)
    assert _ceiling(fs).granted == FLOOR
    # and piling on more good news changes nothing
    fs.extend([F(f"extra-{i}", TOP) for i in range(5)])
    assert _ceiling(fs).granted == FLOOR


def test_worsening_any_factor_never_raises_autonomy():
    # Monotonicity, checked exhaustively over a small space rather than asserted.
    rank = GRADES.rank
    for combo in product(GRADES.levels, repeat=3):
        base = _ceiling([F(str(i), c) for i, c in enumerate(combo)])
        for i in range(3):
            for worse in [c for c in GRADES.levels if rank(c) < rank(combo[i])]:
                lowered = list(combo)
                lowered[i] = worse
                out = _ceiling([F(str(j), c) for j, c in enumerate(lowered)])
                assert rank(out.granted) <= rank(base.granted), (combo, i, worse)


def test_the_grant_never_exceeds_what_was_delegated():
    assert _ceiling(_all(TOP), delegated="L1").granted == "L1"


def test_delegation_capping_is_reported_differently_from_factor_capping():
    # "The situation would permit more than the actor was given" is a different
    # fact from "a factor is holding it back", and reads differently.
    assert _ceiling(_all(TOP), delegated="L2").binding == ()
    assert _ceiling([F("risk", "L2")]).binding == ("risk",)


# --- the binding factor is nameable ------------------------------------------------

def test_the_capping_factor_is_named():
    fs = _all(TOP)
    fs[1] = F("uncertainty", "L1", why="no calibration data for this task")
    out = _ceiling(fs)
    assert out.binding == ("uncertainty",)
    assert "uncertainty" in out.why()


def test_every_factor_at_the_granted_level_is_named():
    out = _ceiling([F("a", "L2"), F("b", "L2"), F("c", "L4")])
    assert out.binding == ("a", "b")


def test_the_reason_survives_into_the_record():
    # A rung with no account of why is a label a supervisor cannot act on.
    out = _ceiling([F("risk", "L2", why="counterparty is unverified")])
    assert out.to_dict()["factors"][0]["why"] == "counterparty is unverified"


# --- unassessed fails closed --------------------------------------------------------

def test_an_unassessed_factor_caps_at_the_floor():
    # Not knowing how uncertain a situation is is not the same as it being
    # certain. Dropping out of the minimum would read as unconstrained.
    fs = _all(TOP)
    fs[1] = F("uncertainty")
    assert _ceiling(fs).granted == FLOOR


def test_unassessed_factors_are_listed_so_the_gap_is_visible():
    assert _ceiling([F("risk", TOP), F("competence")]).unassessed == ("competence",)


def test_an_empty_factor_set_grants_only_what_was_delegated():
    # No claim is invented about a deployment nobody described.
    out = _ceiling([], delegated="L3")
    assert out.granted == "L3" and out.binding == ()


# --- overreach maps onto the existing verdict ------------------------------------------

def test_acting_above_the_ceiling_is_a_finding():
    assert autonomy_verdict(TOP, _ceiling([F("risk", "L2")])) is Verdict.NOT_SATISFIED


def test_acting_within_a_fully_assessed_ceiling_passes():
    assert autonomy_verdict("L2", _ceiling([F("risk", "L3")])) is Verdict.SATISFIED


def test_an_incomplete_assessment_escalates_rather_than_passing():
    esc = _ceiling([F("risk", TOP), F("competence")])
    assert autonomy_verdict(FLOOR, esc) is Verdict.OPEN


def test_an_incomplete_assessment_is_a_gap_not_evidence_of_overreach():
    assert autonomy_verdict(FLOOR, _ceiling([F("competence")])) is not Verdict.NOT_SATISFIED


def test_overreach_is_caught_even_when_the_assessment_is_incomplete():
    # Because the unassessed factor already caps at the floor.
    assert autonomy_verdict("L1", _ceiling([F("competence")])) is Verdict.NOT_SATISFIED


def test_one_step_over_its_ceiling_condemns_the_run():
    good = _ceiling([F("risk", TOP)])
    bad = _ceiling([F("risk", "L1")])
    out = fold_autonomy([("s1", TOP, good), ("s2", TOP, bad)])
    assert out.overall is Verdict.NOT_SATISFIED
    assert [n for n, v in out.issues if v is not Verdict.SATISFIED] == ["s2"]


def test_a_gap_in_the_assessment_dominates_a_failure_elsewhere():
    # OPEN-dominance, inherited from the reused fold: repairing the known
    # overreach must not close a question nobody has yet asked.
    bad = _ceiling([F("risk", "L1")])
    gap = _ceiling([F("competence")])
    out = fold_autonomy([("s1", TOP, bad), ("s2", FLOOR, gap)])
    assert out.overall is Verdict.OPEN


# --- the calculus lowers; restoring is an act -------------------------------------------

def test_restoring_autonomy_requires_naming_the_authorisation():
    with pytest.raises(ValueError):
        relax(TOP, _ceiling([F("risk", TOP)]), authorised_by="  ")


def test_restoring_cannot_go_through_the_current_ceiling():
    assert relax(TOP, _ceiling([F("risk", "L2")]), authorised_by="ticket#4") == "L2"


def test_the_calculus_itself_never_raises_autonomy():
    # Every reachable grant is bounded by the delegation, for any factor set.
    for combo in product(GRADES.levels, repeat=2):
        out = _ceiling([F(str(i), c) for i, c in enumerate(combo)], delegated="L3")
        assert GRADES.rank(out.granted) <= GRADES.rank("L3")


# --- no scores, and no shipped policy -----------------------------------------------------

def test_no_magnitude_is_produced():
    blob = str(_ceiling(_all(TOP)).to_dict()).lower()
    for forbidden in ("score", "weight", "0.", "confidence"):
        assert forbidden not in blob, forbidden


def test_the_kernel_names_no_factor_and_ships_no_ceiling_table():
    # Which factor caps where is a claim about a deployment, and the kernel holds
    # none. If a mapping from a named factor to a rung ever appears here, policy
    # has been smuggled into the mechanism.
    import inspect

    from loomground_solver import escalation as mod
    src = inspect.getsource(mod)
    for term in ("risk", "competence", "context"):
        assert src.lower().count(term) <= 3, f"{term} looks like shipped vocabulary"
    for forbidden in ("def _table", "CEILINGS", "== \"risk\"", "name =="):
        assert forbidden not in src, forbidden


def test_factors_are_opaque_to_the_kernel():
    out = _ceiling([F("Rückabwicklbarkeit", "L2"), F("x-9", TOP)])
    assert out.granted == "L2" and out.binding == ("Rückabwicklbarkeit",)


def test_the_record_round_trips_to_plain_data():
    out = _ceiling([F("risk", "L2", why="w"), F("competence")])
    d = out.to_dict()
    assert d["granted"] == FLOOR and d["delegated"] == TOP
    assert d["ladder"] == list(GRADES.levels)
    assert d["unassessed"] == ["competence"]
    assert d["factors"][1]["ceiling"] is None


def test_an_escalation_can_be_built_without_the_calculus():
    # The dataclass is plain data; a caller reconstructing one from a record must
    # not have to re-run the fold.
    esc = Escalation(granted="L1", binding=("x",), delegated=TOP, ladder=GRADES)
    assert esc.why().startswith("L1:") and esc.unassessed == ()
