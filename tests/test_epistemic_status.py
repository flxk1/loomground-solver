# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Deterministic tests for epistemic_status.

Every case pins a fixed status (or fixed merit verdict) and asserts a fixed
outcome in the *existing* cross_subsumption.Verdict vocabulary. The layer is a
thin tagging + propagation shim: it never defines a parallel verdict, and its
weakest-link fold is issue_aggregation.aggregate_issues reused verbatim — these
tests assert exactly those branches.
"""

import pytest

from loomground_solver import case
from loomground_solver.cross_subsumption import DimVerdict, Verdict
from loomground_solver.dimensions import Dimension
from loomground_solver.epistemic_status import (
    SETTLED,
    UNSETTLED,
    EpistemicStatus,
    StatusedPremise,
    is_settled,
    is_unsettled,
    propagate_derivation,
    propagate_premises,
    propagate_under_condition,
    status_to_verdict,
)

S = Verdict.SATISFIED
N = Verdict.NOT_SATISFIED
O = Verdict.OPEN

ASSERTED = EpistemicStatus.ASSERTED
INFERRED = EpistemicStatus.INFERRED
PRESUPPOSED = EpistemicStatus.PRESUPPOSED
CONTESTED = EpistemicStatus.CONTESTED
UNKNOWN = EpistemicStatus.UNKNOWN


# ── the layer imports and returns the EXISTING Verdict, defines no parallel ─────

def test_layer_reuses_cross_subsumption_verdict_not_a_parallel_type():
    import loomground_solver.epistemic_status as es
    import loomground_solver.cross_subsumption as cs

    # status_to_verdict returns the very same Verdict enum members.
    assert es.status_to_verdict(ASSERTED) is cs.Verdict.SATISFIED
    assert es.status_to_verdict(UNKNOWN) is cs.Verdict.OPEN
    # No parallel three-valued / OPEN type is DEFINED in the module (an enum
    # whose __module__ is this module and that has an OPEN member). The imported
    # cross_subsumption.Verdict is the CONSUMED type — its __module__ is
    # cross_subsumption, so it is correctly excluded.
    import enum

    defined_enums = [
        obj
        for n in dir(es)
        if isinstance(obj := getattr(es, n), type)
        and issubclass(obj, enum.Enum)
        and obj.__module__ == es.__name__
    ]
    assert es.EpistemicStatus in defined_enums
    assert not any("OPEN" in {m.name for m in e} for e in defined_enums)


# ── status classification for all five ──────────────────────────────────────────

@pytest.mark.parametrize("status", [ASSERTED, INFERRED])
def test_settled_classification(status):
    assert is_settled(status) is True
    assert is_unsettled(status) is False
    assert status in SETTLED


@pytest.mark.parametrize("status", [PRESUPPOSED, CONTESTED, UNKNOWN])
def test_unsettled_classification(status):
    assert is_unsettled(status) is True
    assert is_settled(status) is False
    assert status in UNSETTLED


def test_settled_and_unsettled_partition_the_lattice():
    all_five = set(EpistemicStatus)
    assert SETTLED | UNSETTLED == all_five
    assert SETTLED & UNSETTLED == set()


# ── status → Verdict map: settled passes, unsettled escalates, never NOT_SAT ─────

@pytest.mark.parametrize("status", [ASSERTED, INFERRED])
def test_settled_maps_to_satisfied(status):
    assert status_to_verdict(status) is S


@pytest.mark.parametrize("status", [PRESUPPOSED, CONTESTED, UNKNOWN])
def test_unsettled_maps_to_open(status):
    assert status_to_verdict(status) is O


def test_status_never_maps_to_not_satisfied():
    # Falsification-on-the-merits is subsume_across' job, never a status.
    for status in EpistemicStatus:
        assert status_to_verdict(status) is not N


# ── BRANCH: a settled (ASSERTED) premise passes through ──────────────────────────

def test_single_asserted_premise_passes_through_to_satisfied():
    fact = case.Fact(text="the invoice was delivered", source="Exhibit A")
    p = StatusedPremise(name="delivered", status=ASSERTED, fact=fact)
    res = propagate_premises([p])
    assert res.overall is S
    assert res.satisfied is True
    assert res.open is False
    # references the Fact by identity, does not mutate/require it
    assert p.fact is fact
    assert not hasattr(fact, "status")


def test_settled_premises_let_the_merit_verdict_pass_through():
    # Under a condition decided NOT_SATISFIED on the merits, with only settled
    # premises, the fold reflects the merit verdict (NOT_SATISFIED) — status did
    # not add an OPEN.
    cond = DimVerdict("cond", Dimension.INTENTIONAL, N, reason="unproven on merits")
    p = StatusedPremise(name="basis", status=ASSERTED)
    res = propagate_under_condition("cond", cond, [p])
    assert res.overall is N
    assert res.open is False


# ── BRANCH: a single UNSETTLED premise → OPEN ────────────────────────────────────

@pytest.mark.parametrize("status", [PRESUPPOSED, CONTESTED, UNKNOWN])
def test_single_unsettled_premise_is_open(status):
    p = StatusedPremise(name="shaky", status=status)
    res = propagate_premises([p])
    assert res.overall is O
    assert res.open is True


def test_unsettled_premise_opens_even_under_a_satisfied_condition():
    # Condition met on the merits, but a CONTESTED premise → OPEN dominates.
    cond = DimVerdict("cond", Dimension.INTENTIONAL, S, reason="holds on merits")
    p = StatusedPremise(name="disputed-basis", status=CONTESTED)
    res = propagate_under_condition("cond", cond, [p])
    assert res.overall is O


# ── BRANCH: all-settled derivation → settled ─────────────────────────────────────

def test_all_settled_premises_derivation_is_settled():
    premises = [
        StatusedPremise("p1", ASSERTED),
        StatusedPremise("p2", INFERRED),
        StatusedPremise("p3", ASSERTED),
    ]
    res = propagate_premises(premises)
    assert res.overall is S
    # every premise carried through the fold, in order
    assert res.issues == (("p1", S), ("p2", S), ("p3", S))


def test_all_settled_derivation_with_satisfied_conclusion_is_satisfied():
    premises = [StatusedPremise("p1", ASSERTED), StatusedPremise("p2", INFERRED)]
    conclusion = DimVerdict("concl", Dimension.INTENTIONAL, S)
    res = propagate_derivation(premises, conclusion)
    assert res.overall is S


# ── BRANCH: one unsettled among settled → OPEN (weakest-link, OPEN dominates) ────

def test_one_unsettled_among_settled_is_open_weakest_link():
    premises = [
        StatusedPremise("p1", ASSERTED),
        StatusedPremise("p2", PRESUPPOSED),  # the weak link
        StatusedPremise("p3", INFERRED),
    ]
    res = propagate_premises(premises)
    assert res.overall is O
    assert res.open is True


def test_weakest_link_holds_end_to_end_in_a_derivation():
    # All premises settled but one, and the conclusion satisfied on the merits:
    # the single unsettled premise still opens the whole derivation.
    premises = [
        StatusedPremise("p1", ASSERTED),
        StatusedPremise("p2", UNKNOWN),  # weak link
    ]
    conclusion = DimVerdict("concl", Dimension.INTENTIONAL, S)
    res = propagate_derivation(premises, conclusion)
    assert res.overall is O


def test_open_dominates_a_not_satisfied_sibling():
    # A NOT_SATISFIED merit condition and an UNSETTLED premise together → OPEN
    # dominates NOT_SATISFIED (the reused aggregate_issues rule).
    cond = DimVerdict("cond", Dimension.INTENTIONAL, N)
    p = StatusedPremise("shaky", CONTESTED)
    res = propagate_under_condition("cond", cond, [p])
    assert res.overall is O


# ── empty set base case (inherited from aggregate_issues) ────────────────────────

def test_empty_premise_set_is_vacuously_satisfied():
    res = propagate_premises([])
    assert res.overall is S


# ── Ground (norm-side premise) works the same, still no status field on it ───────

def test_ground_premise_pairs_without_mutating_case_ground():
    g = case.Ground(pinpoint="GDPR Art. 17(1)", condition="request made")
    p = StatusedPremise(name="norm-basis", status=PRESUPPOSED, fact=g)
    res = propagate_premises([p])
    assert res.overall is O
    assert p.fact is g
    assert not hasattr(g, "status")
