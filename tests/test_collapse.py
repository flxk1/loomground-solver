# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Conjunctive collapse: weakest-link, never a product.

Two things are defended here. That one term at its floor prevents the whole from
passing however strong the rest are — the collapse itself. And that a measured
floor stays distinguishable from an unmeasured constituent, because "we know this
is broken" and "nobody looked" call for different actions and a two-valued
mapping would report them identically.
"""
from __future__ import annotations

from loomground_solver.collapse import (
    Constituent as C, ConstituentState as St, collapse, state_to_verdict,
)
from loomground_solver.cross_subsumption import Verdict

# The caller's vocabulary, not the kernel's — used here only as test data.
FIVE = ("observability", "intervenability", "comprehensibility",
        "authority", "timeliness")


def _all(state):
    return [C(n, state) for n in FIVE]


# --- the collapse ---------------------------------------------------------------

def test_a_healthy_conjunction_passes():
    assert collapse(_all(St.PRESENT)).overall is Verdict.SATISFIED


def test_one_term_at_its_floor_prevents_the_whole_from_passing():
    for i, name in enumerate(FIVE):
        cs = _all(St.PRESENT)
        cs[i] = C(name, St.AT_FLOOR)
        assert collapse(cs).overall is not Verdict.SATISFIED, name


def test_strong_terms_cannot_compensate_for_a_collapsed_one():
    # The trap this module exists to avoid. Under a product-of-scores reading,
    # four excellent terms could outweigh one zero. Under a conjunction they
    # cannot, and that is the whole distinction between formally present and
    # functionally absent.
    cs = _all(St.PRESENT) + [C("extra-strong", St.PRESENT)]
    cs[0] = C(FIVE[0], St.AT_FLOOR)
    assert collapse(cs).overall is not Verdict.SATISFIED


def test_the_aggregate_says_which_term_collapsed_it():
    cs = _all(St.PRESENT)
    cs[4] = C("timeliness", St.AT_FLOOR)
    out = collapse(cs)
    failing = [n for n, v in out.issues if v is not Verdict.SATISFIED]
    assert failing == ["timeliness"]


# --- measured zero vs unmeasured -------------------------------------------------

def test_a_measured_floor_is_a_finding():
    assert state_to_verdict(St.AT_FLOOR) is Verdict.NOT_SATISFIED


def test_an_unmeasured_constituent_is_an_open_question():
    assert state_to_verdict(St.UNASSIGNED) is Verdict.OPEN


def test_the_two_are_never_collapsed_into_one_value():
    # If these ever coincide, "we know it is broken" and "nobody looked" have
    # become the same report.
    assert state_to_verdict(St.AT_FLOOR) is not state_to_verdict(St.UNASSIGNED)


def test_an_unmeasured_term_dominates_a_measured_failure():
    # OPEN-dominance, inherited from the reused fold and correct here: repairing
    # the known failure must not close a question nobody has yet asked.
    out = collapse([C("a", St.AT_FLOOR), C("b", St.UNASSIGNED), C("c", St.PRESENT)])
    assert out.overall is Verdict.OPEN


def test_unassigned_never_reads_as_present():
    assert collapse(_all(St.UNASSIGNED)).overall is not Verdict.SATISFIED


# --- it computes no product and ships no vocabulary ------------------------------

def test_the_kernel_names_no_constituent():
    # A decomposition is a claim about a subject area, and this kernel holds none.
    import inspect

    from loomground_solver import collapse as mod
    src = inspect.getsource(mod).lower()
    for term in ("observability", "intervenability", "authority", "timeliness"):
        assert src.count(term) <= 2, f"{term} looks like shipped vocabulary"


def test_no_score_or_magnitude_is_produced():
    out = collapse(_all(St.PRESENT))
    blob = str(out).lower()
    for forbidden in ("score", "product", "0.", "magnitude"):
        assert forbidden not in blob, forbidden


def test_the_fold_is_the_existing_aggregation():
    # Every constituent must survive as a sub-issue; if they stop doing so, a
    # parallel aggregation has been grown beside the real one.
    out = collapse(_all(St.PRESENT))
    assert {n for n, _ in out.issues} == set(FIVE)


def test_an_empty_conjunction_invents_nothing():
    out = collapse([])
    assert out.overall is Verdict.SATISFIED  # the aggregation's own base case
    assert out.issues == ()


def test_a_constituent_may_record_how_its_state_was_established():
    # Matters most for a constituent that cannot be read off a system at all and
    # has to be measured against people.
    c = C("comprehensibility", St.UNASSIGNED, note="no reader was tested")
    assert c.to_dict()["note"] == "no reader was tested"
