# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Falsifiability: rank evidence by how it could be shown wrong.

Two properties carry the module. First, a conclusion resting **solely** on a
self-report escalates — that is the commitment made mechanical, and it is the one
test that must never be relaxed to make something else pass. Second, the rank
reuses the existing honesty verdict and never mints a new one: weak support means
escalate, not false.
"""
from __future__ import annotations

import pytest

from loomground_solver.cross_subsumption import Verdict
from loomground_solver.falsifiability import (
    SUPPORT_FLOOR, Evidence, Falsifiability as F, best_support, fold_support,
    rank, support_verdict,
)


# --- the ordering is the content ------------------------------------------------

def test_the_ordering_runs_from_unfalsifiable_to_re_derivable():
    assert (F.SELF_REPORT < F.DECLARED_PLAN < F.OBSERVED_TOOL_CALL
            < F.VERIFIED_OUTCOME < F.SPAN_GROUNDED < F.REPLAYABLE)


def test_self_report_is_the_weakest_and_replayable_the_strongest():
    assert min(F) is F.SELF_REPORT
    assert max(F) is F.REPLAYABLE


# --- the commitment, made mechanical --------------------------------------------

def test_a_conclusion_resting_solely_on_a_self_report_escalates():
    # The load-bearing test. A self-report may inform a decision; it may never be
    # the sole basis for one.
    assert support_verdict([F.SELF_REPORT]) is Verdict.OPEN
    assert support_verdict([Evidence("chain-of-thought", F.SELF_REPORT)]) is Verdict.OPEN


def test_the_default_floor_is_exactly_one_step_above_self_report():
    # The weakest rule that implements the commitment. Anything lower licenses
    # precisely what the ordering exists to prevent.
    assert SUPPORT_FLOOR is F.DECLARED_PLAN


def test_a_self_report_still_counts_when_something_else_carries_the_claim():
    # Last in the ordering, not excluded from it — it may inform.
    assert support_verdict([F.SELF_REPORT, F.DECLARED_PLAN]) is Verdict.SATISFIED


def test_absent_evidence_escalates_rather_than_passing():
    assert support_verdict([]) is Verdict.OPEN
    assert best_support([]) is None


def test_a_deployment_may_raise_the_floor():
    assert support_verdict([F.OBSERVED_TOOL_CALL]) is Verdict.SATISFIED
    assert support_verdict([F.OBSERVED_TOOL_CALL],
                           floor=F.SPAN_GROUNDED) is Verdict.OPEN


# --- it mints no vocabulary -----------------------------------------------------

def test_a_rank_never_emits_not_satisfied():
    # How a claim could be falsified is orthogonal to whether it is true. Weak
    # support escalates; declaring a claim false belongs to the merits layer.
    for level in F:
        for floor in F:
            assert support_verdict([level], floor=floor) is not Verdict.NOT_SATISFIED


def test_verdicts_are_the_existing_three_valued_ones():
    assert support_verdict([F.REPLAYABLE]) in set(Verdict)


# --- strongest support for one claim, weakest link across claims ----------------

def test_the_strongest_support_for_a_claim_wins():
    # One replayable derivation is not weakened by sitting beside a self-report.
    assert best_support([F.SELF_REPORT, F.REPLAYABLE]) is F.REPLAYABLE


def test_weakest_link_applies_across_the_claims_a_conclusion_needs():
    out = fold_support([
        ("tool was called", [Evidence("log#42", F.OBSERVED_TOOL_CALL)]),
        ("source says so", [Evidence("doc#7:120-180", F.SPAN_GROUNDED)]),
        ("it intended no harm", [Evidence("cot", F.SELF_REPORT)]),
    ])
    assert out.overall is Verdict.OPEN, "one unfalsifiable claim must dominate"


def test_a_well_supported_conclusion_folds_satisfied():
    out = fold_support([
        ("a", [F.SPAN_GROUNDED]),
        ("b", [F.REPLAYABLE]),
    ])
    assert out.overall is Verdict.SATISFIED


def test_the_fold_is_the_existing_aggregation_not_a_reimplementation():
    # If this ever stops carrying sub-issues, a parallel fold has been grown.
    out = fold_support([("a", [F.REPLAYABLE]), ("b", [F.SELF_REPORT])])
    assert {name for name, _ in out.issues} == {"a", "b"}
    assert out.reason


# --- the rank is asserted, never inferred ---------------------------------------

def test_rank_accepts_an_object_a_member_or_a_name():
    assert rank(Evidence("x", F.REPLAYABLE)) is F.REPLAYABLE
    assert rank(F.SPAN_GROUNDED) is F.SPAN_GROUNDED
    assert rank("verified_outcome") is F.VERIFIED_OUTCOME


def test_an_unknown_rank_name_raises_rather_than_defaulting():
    # Defaulting an unrecognised rank would quietly admit unranked evidence.
    with pytest.raises(KeyError):
        rank("probably_fine")


def test_evidence_names_itself_so_a_reader_can_go_and_look():
    e = Evidence("doc#7:120-180", F.SPAN_GROUNDED)
    assert e.to_dict() == {"ref": "doc#7:120-180", "falsifiability": "SPAN_GROUNDED"}
