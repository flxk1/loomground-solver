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
"""
from __future__ import annotations

from itertools import product

import pytest

from loomground_solver.cross_subsumption import Verdict
from loomground_solver.escalation import (
    FLOOR, Autonomy as A, Escalation, Factor as F,
    autonomy_verdict, ceiling, fold_autonomy, relax,
)

# The caller's vocabulary, not the kernel's — test data only.
FIVE = ("risk", "uncertainty", "reversibility", "context", "competence")


def _all(level):
    return [F(n, level) for n in FIVE]


# --- the lowest ceiling wins ------------------------------------------------------

def test_the_lowest_ceiling_is_what_is_granted():
    fs = _all(A.ACT)
    fs[2] = F("reversibility", A.CONFIRM)
    assert ceiling(fs, delegated=A.ACT).granted is A.CONFIRM


def test_no_factor_compensates_for_another():
    # The trap. Under a weighted sum, four factors at the top could outweigh one
    # at the bottom. Competence does not make an irreversible act reversible.
    fs = _all(A.ACT)
    fs[2] = F("reversibility", A.SUSPENDED)
    assert ceiling(fs, delegated=A.ACT).granted is A.SUSPENDED
    # and piling on more good news changes nothing
    fs.extend([F(f"extra-{i}", A.ACT) for i in range(5)])
    assert ceiling(fs, delegated=A.ACT).granted is A.SUSPENDED


def test_worsening_any_factor_never_raises_autonomy():
    # Monotonicity, checked exhaustively over a small space rather than asserted.
    for combo in product(list(A), repeat=3):
        base = ceiling([F(str(i), c) for i, c in enumerate(combo)], delegated=A.ACT)
        for i in range(3):
            for worse in [c for c in A if c < combo[i]]:
                lowered = list(combo)
                lowered[i] = worse
                out = ceiling([F(str(j), c) for j, c in enumerate(lowered)],
                              delegated=A.ACT)
                assert out.granted <= base.granted, (combo, i, worse)


def test_the_grant_never_exceeds_what_was_delegated():
    assert ceiling(_all(A.ACT), delegated=A.PROPOSE).granted is A.PROPOSE


def test_delegation_capping_is_reported_differently_from_factor_capping():
    # "The situation would permit more than the actor was given" is a different
    # fact from "a factor is holding it back", and reads differently.
    by_delegation = ceiling(_all(A.ACT), delegated=A.CONFIRM)
    assert by_delegation.binding == ()
    by_factor = ceiling([F("risk", A.CONFIRM)], delegated=A.ACT)
    assert by_factor.binding == ("risk",)


# --- the binding factor is nameable ------------------------------------------------

def test_the_capping_factor_is_named():
    fs = _all(A.ACT)
    fs[1] = F("uncertainty", A.PROPOSE, why="no calibration data for this task")
    out = ceiling(fs, delegated=A.ACT)
    assert out.binding == ("uncertainty",)
    assert "uncertainty" in out.why()


def test_every_factor_at_the_granted_level_is_named():
    out = ceiling([F("a", A.CONFIRM), F("b", A.CONFIRM), F("c", A.ACT)],
                  delegated=A.ACT)
    assert out.binding == ("a", "b")


def test_the_reason_survives_into_the_record():
    # A rung with no account of why is a number a supervisor cannot act on.
    out = ceiling([F("risk", A.CONFIRM, why="counterparty is unverified")],
                  delegated=A.ACT)
    assert out.to_dict()["factors"][0]["why"] == "counterparty is unverified"


# --- unassessed fails closed --------------------------------------------------------

def test_an_unassessed_factor_caps_at_the_floor():
    # Not knowing how uncertain a situation is is not the same as it being
    # certain. Dropping out of the minimum would read as unconstrained.
    fs = _all(A.ACT)
    fs[1] = F("uncertainty")
    assert ceiling(fs, delegated=A.ACT).granted is FLOOR


def test_unassessed_factors_are_listed_so_the_gap_is_visible():
    out = ceiling([F("risk", A.ACT), F("competence")], delegated=A.ACT)
    assert out.unassessed == ("competence",)


def test_an_empty_factor_set_grants_only_what_was_delegated():
    # No claim is invented about a deployment nobody described.
    out = ceiling([], delegated=A.NOTIFY)
    assert out.granted is A.NOTIFY and out.binding == ()


# --- the rungs stay distinct ---------------------------------------------------------

def test_positive_approval_and_absence_of_objection_are_different_rungs():
    # Routinely conflated, and the second is much weaker oversight. Recording it
    # as the first overstates the control that was actually exercised.
    assert A.CONFIRM < A.NOTIFY
    assert A.CONFIRM is not A.NOTIFY


def test_the_ladder_is_ordered_and_bottoms_out_at_suspended():
    assert min(A) is A.SUSPENDED is FLOOR
    assert max(A) is A.ACT


# --- overreach maps onto the existing verdict ------------------------------------------

def test_acting_above_the_ceiling_is_a_finding():
    esc = ceiling([F("risk", A.CONFIRM)], delegated=A.ACT)
    assert autonomy_verdict(A.ACT, esc) is Verdict.NOT_SATISFIED


def test_acting_within_a_fully_assessed_ceiling_passes():
    esc = ceiling([F("risk", A.NOTIFY)], delegated=A.ACT)
    assert autonomy_verdict(A.CONFIRM, esc) is Verdict.SATISFIED


def test_an_incomplete_assessment_escalates_rather_than_passing():
    esc = ceiling([F("risk", A.ACT), F("competence")], delegated=A.ACT)
    assert autonomy_verdict(A.SUSPENDED, esc) is Verdict.OPEN


def test_an_incomplete_assessment_is_a_gap_not_evidence_of_overreach():
    esc = ceiling([F("competence")], delegated=A.ACT)
    assert autonomy_verdict(FLOOR, esc) is not Verdict.NOT_SATISFIED


def test_overreach_is_caught_even_when_the_assessment_is_incomplete():
    # Because the unassessed factor already caps at the floor.
    esc = ceiling([F("competence")], delegated=A.ACT)
    assert autonomy_verdict(A.PROPOSE, esc) is Verdict.NOT_SATISFIED


def test_one_step_over_its_ceiling_condemns_the_run():
    good = ceiling([F("risk", A.ACT)], delegated=A.ACT)
    bad = ceiling([F("risk", A.PROPOSE)], delegated=A.ACT)
    out = fold_autonomy([("s1", A.ACT, good), ("s2", A.ACT, bad)])
    assert out.overall is Verdict.NOT_SATISFIED
    assert [n for n, v in out.issues if v is not Verdict.SATISFIED] == ["s2"]


def test_a_gap_in_the_assessment_dominates_a_failure_elsewhere():
    # OPEN-dominance, inherited from the reused fold: repairing the known
    # overreach must not close a question nobody has yet asked.
    bad = ceiling([F("risk", A.PROPOSE)], delegated=A.ACT)
    gap = ceiling([F("competence")], delegated=A.ACT)
    out = fold_autonomy([("s1", A.ACT, bad), ("s2", FLOOR, gap)])
    assert out.overall is Verdict.OPEN


# --- the calculus lowers; restoring is an act -------------------------------------------

def test_restoring_autonomy_requires_naming_the_authorisation():
    esc = ceiling([F("risk", A.ACT)], delegated=A.ACT)
    with pytest.raises(ValueError):
        relax(A.ACT, esc, authorised_by="  ")


def test_restoring_cannot_go_through_the_current_ceiling():
    esc = ceiling([F("risk", A.CONFIRM)], delegated=A.ACT)
    assert relax(A.ACT, esc, authorised_by="ticket#4") is A.CONFIRM


def test_the_calculus_itself_never_raises_autonomy():
    # Every reachable grant is bounded by the delegation, for any factor set.
    for combo in product(list(A), repeat=2):
        out = ceiling([F(str(i), c) for i, c in enumerate(combo)], delegated=A.NOTIFY)
        assert out.granted <= A.NOTIFY


# --- no scores, and no shipped policy -----------------------------------------------------

def test_no_magnitude_is_produced():
    out = ceiling(_all(A.ACT), delegated=A.ACT)
    blob = str(out.to_dict()).lower()
    for forbidden in ("score", "weight", "0.", "confidence"):
        assert forbidden not in blob, forbidden


def test_the_kernel_names_no_factor_and_ships_no_ceiling_table():
    # Which factor caps where is a claim about a deployment, and the kernel holds
    # none. If a mapping from a named factor to a rung ever appears here, policy
    # has been smuggled into the mechanism.
    import inspect

    from loomground_solver import escalation as mod
    src = inspect.getsource(mod).lower()
    for term in ("risk", "competence", "context"):
        assert src.count(term) <= 3, f"{term} looks like shipped vocabulary"
    # and no factor name is ever compared against, which is how a table would work
    for forbidden in ("def _table", "CEILINGS", "== \"risk\"", "name =="):
        assert forbidden not in inspect.getsource(mod), forbidden


def test_factors_are_opaque_to_the_kernel():
    # Any identifiers work; the kernel compares ceilings and reads no names.
    out = ceiling([F("Rückabwicklbarkeit", A.CONFIRM), F("x-9", A.ACT)],
                  delegated=A.ACT)
    assert out.granted is A.CONFIRM and out.binding == ("Rückabwicklbarkeit",)


def test_the_record_round_trips_to_plain_data():
    out = ceiling([F("risk", A.CONFIRM, why="w"), F("competence")], delegated=A.ACT)
    d = out.to_dict()
    assert d["granted"] == "SUSPENDED" and d["delegated"] == "ACT"
    assert d["unassessed"] == ["competence"]
    assert d["factors"][1]["ceiling"] is None


def test_an_escalation_can_be_built_without_the_calculus():
    # The dataclass is plain data; a caller reconstructing one from a record must
    # not have to re-run the fold.
    esc = Escalation(granted=A.PROPOSE, binding=("x",), delegated=A.ACT)
    assert esc.why().startswith("PROPOSE:") and esc.unassessed == ()
