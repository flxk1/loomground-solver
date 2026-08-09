# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Formal justice screen (O154, formal half) — FLAG ONLY: composes the O151
consistency checks and the O152 adverse-impact flag, recommends DETERMINATE ->
ESCALATE when any trips, and never emits a verdict."""
from __future__ import annotations

import dataclasses

import pytest

from loomground_solver.consistency import ConsistencyReport, DecidedCase
from loomground_solver.distribution import ImpactRatio
from loomground_solver.relation import ESCALATE as _ESCALATE
from loomground_solver.justice_screen import (
    ADVERSE_IMPACT,
    DETERMINATE,
    DISCRIMINATION,
    ESCALATE,
    INCONSISTENCY,
    ScreenResult,
    TrippedReason,
    justice_screen,
)


# ── clean case set: nothing trips, disposition unchanged ─────────────────────

def test_clean_set_does_not_recommend_demotion():
    cases = [DecidedCase("a", {"harm": "yes"}, "liable"),
             DecidedCase("b", {"harm": "yes"}, "liable"),
             DecidedCase("c", {"harm": "no"}, "not-liable")]
    r = justice_screen("a", cases, relevant_keys={"harm"})
    assert r.demote is False
    assert r.reasons == ()
    assert r.recommended == DETERMINATE
    assert r.disposition == DETERMINATE
    assert r.consistency.consistent is True


# ── O151 treat-like-alike breach trips the screen ────────────────────────────

def test_inconsistency_recommends_escalation():
    cases = [DecidedCase("a", {"harm": "yes", "hair": "red"}, "liable"),
             DecidedCase("b", {"harm": "yes", "hair": "blue"}, "not-liable")]
    r = justice_screen("a", cases, relevant_keys={"harm"})
    assert r.demote is True
    assert r.recommended == ESCALATE
    assert [x.check for x in r.reasons] == [INCONSISTENCY]
    assert r.reasons[0].detail["pairs"][0]["kind"] == "irrelevant-feature"


# ── O151 direct-discrimination specialisation (opt-in) ───────────────────────

def test_discrimination_trips_only_when_protected_keys_supplied():
    cases = [DecidedCase("a", {"skill": "high", "gender": "f"}, "reject"),
             DecidedCase("b", {"skill": "high", "gender": "m"}, "hire")]
    # without protected_keys the outcome-flip is a plain inconsistency
    plain = justice_screen("a", cases, relevant_keys={"skill"})
    assert [x.check for x in plain.reasons] == [INCONSISTENCY]
    assert plain.nondiscrimination is None
    # with protected_keys the specialisation also fires
    prot = justice_screen("a", cases, relevant_keys={"skill"},
                          protected_keys={"gender"})
    codes = {x.check for x in prot.reasons}
    assert DISCRIMINATION in codes
    assert prot.nondiscrimination is not None
    assert prot.recommended == ESCALATE


# ── O152 adverse-impact flag (opt-in, aggregate) ─────────────────────────────

def test_adverse_impact_breach_recommends_escalation():
    cases = [DecidedCase("c1", {"g": "f"}, "reject"),
             DecidedCase("c2", {"g": "f"}, "reject"),
             DecidedCase("c3", {"g": "m"}, "hire"),
             DecidedCase("c4", {"g": "m"}, "hire")]
    # every relevant signature is unique, so consistency itself is clean;
    # the disparity is what trips the screen.
    r = justice_screen("c1", cases, relevant_keys={"g"},
                       group_key="g", favourable={"hire"})
    assert [x.check for x in r.reasons] == [ADVERSE_IMPACT]
    assert r.impact is not None
    assert r.impact.breaches is True
    assert r.demote is True


# ── focal_only narrows the pairwise checks to the case under screen ──────────

def test_focal_only_ignores_defects_not_touching_the_focal_case():
    # the inconsistent pair is (b, c); the focal case 'a' is clean.
    cases = [DecidedCase("a", {"r": 1}, "yes"),
             DecidedCase("b", {"r": 2, "z": 1}, "yes"),
             DecidedCase("c", {"r": 2, "z": 2}, "no")]
    whole = justice_screen("a", cases, relevant_keys={"r"})
    assert whole.demote is True  # a defect exists somewhere in the set
    focal = justice_screen("a", cases, relevant_keys={"r"}, focal_only=True)
    assert focal.demote is False  # ...but not one touching 'a'
    assert focal.recommended == DETERMINATE
    # the full report is still carried for transparency
    assert focal.consistency.consistent is False


# ── FLAG-ONLY boundary: no verdict, label sourced, disposition untouched ─────

def test_flag_only_boundary_no_verdict_and_sourced_label():
    cases = [DecidedCase("a", {"harm": "yes", "hair": "red"}, "liable"),
             DecidedCase("b", {"harm": "yes", "hair": "blue"}, "not-liable")]
    r = justice_screen("a", cases, relevant_keys={"harm"})
    d = r.to_dict()
    # the screen recommends; it never labels the decision
    for banned in ("unjust", "just", "verdict", "decision", "unlawful"):
        assert banned not in d
    # ESCALATE label is the package's one escalation token, not a fresh literal
    assert ESCALATE == str(_ESCALATE) == "ESCALATE"
    # it recommends, it does not mutate: the incoming disposition is preserved
    assert r.disposition == DETERMINATE
    assert d["recommended"] == ESCALATE and d["demote"] is True
    assert isinstance(r, ScreenResult)
    assert isinstance(r.consistency, ConsistencyReport)


# ── multiple checks can trip together, in a stable order ─────────────────────

def test_multiple_reasons_are_stable_ordered():
    cases = [DecidedCase("a", {"skill": "high", "gender": "f"}, "reject"),
             DecidedCase("b", {"skill": "high", "gender": "m"}, "hire")]
    r = justice_screen("a", cases, relevant_keys={"skill"},
                       protected_keys={"gender"},
                       group_key="gender", favourable={"hire"})
    codes = [x.check for x in r.reasons]
    assert codes == sorted(codes)
    assert set(codes) >= {INCONSISTENCY, DISCRIMINATION, ADVERSE_IMPACT}


def test_reasons_and_result_are_frozen():
    cases = [DecidedCase("a", {"harm": "yes", "hair": "red"}, "liable"),
             DecidedCase("b", {"harm": "yes", "hair": "blue"}, "not-liable")]
    r = justice_screen("a", cases, relevant_keys={"harm"})
    assert isinstance(r.reasons[0], TrippedReason)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.demote = False  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.reasons[0].check = "x"  # type: ignore[misc]
