# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Universalizability / treat-like-alike (O151): outcomes must be a function of
the legally-relevant features only; protected-attribute mode is direct
discrimination."""
from __future__ import annotations

from loomground_solver.case import CaseRecord
from loomground_solver.consistency import (
    DISCRIMINATION,
    IRRELEVANT,
    ConsistencyReport,
    DecidedCase,
    InconsistentPair,
    check_consistency,
    check_nondiscrimination,
    decided_case_from_record,
    terminal_state,
)


# ── check_consistency ────────────────────────────────────────────────────────

def test_like_cases_decided_unalike_is_inconsistent():
    rep = check_consistency(
        [DecidedCase("a", {"harm": "yes", "hair": "red"}, "liable"),
         DecidedCase("b", {"harm": "yes", "hair": "blue"}, "not-liable")],
        relevant_keys={"harm"},
    )
    assert rep.consistent is False
    assert len(rep.pairs) == 1
    p = rep.pairs[0]
    assert (p.left, p.right) == ("a", "b")
    assert p.kind == IRRELEVANT
    assert p.differing_keys == ("hair",)
    assert {p.left_outcome, p.right_outcome} == {"liable", "not-liable"}


def test_outcome_tracking_relevant_feature_is_consistent():
    rep = check_consistency(
        [DecidedCase("a", {"harm": "yes"}, "liable"),
         DecidedCase("b", {"harm": "no"}, "not-liable")],
        relevant_keys={"harm"},
    )
    assert rep.consistent is True
    assert rep.pairs == ()


def test_clean_function_of_relevant_features_is_consistent():
    rep = check_consistency(
        [DecidedCase("a", {"sev": 1}, "low"),
         DecidedCase("b", {"sev": 1}, "low"),
         DecidedCase("c", {"sev": 2}, "high")],
        relevant_keys={"sev"},
    )
    assert rep.consistent is True
    assert rep.pairs == ()


def test_empty_and_single_case_are_vacuously_consistent():
    assert check_consistency([], relevant_keys={"harm"}).consistent is True
    assert check_consistency(
        [DecidedCase("a", {"harm": "yes"}, "liable")],
        relevant_keys={"harm"}).consistent is True


def test_missing_relevant_key_is_a_distinct_value():
    # 'a' omits the relevant key entirely; 'b' sets it. They do NOT share a
    # relevant signature, so the differing outcome is legitimate.
    rep = check_consistency(
        [DecidedCase("a", {}, "liable"),
         DecidedCase("b", {"harm": "yes"}, "not-liable")],
        relevant_keys={"harm"},
    )
    assert rep.consistent is True


def test_no_relevant_keys_means_every_outcome_must_match():
    # with an empty relevant set all cases are "alike"; differing outcomes clash
    rep = check_consistency(
        [DecidedCase("a", {"x": 1}, "yes"),
         DecidedCase("b", {"x": 2}, "no")],
        relevant_keys=set(),
    )
    assert rep.consistent is False
    assert rep.pairs[0].differing_keys == ("x",)


def test_pairs_are_order_stable_by_left_then_right():
    rep = check_consistency(
        [DecidedCase("c", {"r": 1, "z": 3}, "yes"),
         DecidedCase("a", {"r": 1, "z": 4}, "no"),
         DecidedCase("b", {"r": 1, "z": 5}, "no")],
        relevant_keys={"r"},
    )
    got = [(p.left, p.right) for p in rep.pairs]
    assert got == sorted(got)
    # endpoints within a pair are ordered too
    for p in rep.pairs:
        assert p.left <= p.right


# ── check_nondiscrimination ──────────────────────────────────────────────────

def test_flip_on_protected_attribute_only_is_discrimination():
    rep = check_nondiscrimination(
        [DecidedCase("a", {"skill": "high", "gender": "f"}, "reject"),
         DecidedCase("b", {"skill": "high", "gender": "m"}, "hire")],
        protected_keys={"gender"},
    )
    assert rep.consistent is False
    assert len(rep.pairs) == 1
    p = rep.pairs[0]
    assert (p.left, p.right) == ("a", "b")
    assert p.kind == DISCRIMINATION
    assert p.differing_keys == ("gender",)


def test_legitimate_difference_present_is_not_discrimination():
    rep = check_nondiscrimination(
        [DecidedCase("a", {"skill": "low", "gender": "f"}, "reject"),
         DecidedCase("b", {"skill": "high", "gender": "m"}, "hire")],
        protected_keys={"gender"},
    )
    assert rep.consistent is True
    assert rep.pairs == ()


def test_same_protected_attr_differing_outcome_is_not_flagged():
    # both female, only skill differs -> they are not "like" on the controls
    rep = check_nondiscrimination(
        [DecidedCase("a", {"skill": "low", "gender": "f"}, "reject"),
         DecidedCase("b", {"skill": "high", "gender": "f"}, "hire")],
        protected_keys={"gender"},
    )
    assert rep.consistent is True


def test_identical_including_protected_and_same_outcome_is_consistent():
    rep = check_nondiscrimination(
        [DecidedCase("a", {"skill": "high", "gender": "f"}, "hire"),
         DecidedCase("b", {"skill": "high", "gender": "f"}, "hire")],
        protected_keys={"gender"},
    )
    assert rep.consistent is True


# ── CaseRecord adapter ───────────────────────────────────────────────────────

def _record(resolution: dict) -> CaseRecord:
    return CaseRecord(problem={"text": "q"}, grounds=[], chain=[], gaps=[],
                      resolution=resolution)


def test_terminal_state_determinate():
    rec = _record({"type": "determinate", "answer": "act: prohibited"})
    assert terminal_state(rec) == "act: prohibited"


def test_terminal_state_residual_with_choice():
    rec = _record({"type": "residual", "surface": {},
                   "choice": {"chosen_label": "escalate"}})
    assert terminal_state(rec) == "escalate"


def test_terminal_state_open_when_no_choice():
    rec = _record({"type": "residual", "surface": {}, "choice": None})
    assert terminal_state(rec) == "open"
    assert terminal_state(_record({})) == "open"


def test_decided_case_from_record_consumes_caserecord():
    rec = _record({"type": "determinate", "answer": "act: prohibited"})
    dc = decided_case_from_record("c1", {"harm": "yes"}, rec)
    assert isinstance(dc, DecidedCase)
    assert dc.id == "c1"
    assert dc.outcome == "act: prohibited"
    assert dc.features["harm"] == "yes"


def test_records_feed_the_consistency_check():
    # two decided records with the same relevant feature but opposite outcomes
    rec_liable = _record({"type": "determinate", "answer": "liable"})
    rec_not = _record({"type": "determinate", "answer": "not-liable"})
    a = decided_case_from_record("a", {"harm": "yes", "hair": "red"}, rec_liable)
    b = decided_case_from_record("b", {"harm": "yes", "hair": "blue"}, rec_not)
    rep = check_consistency([a, b], relevant_keys={"harm"})
    assert rep.consistent is False
    assert rep.pairs[0].kind == IRRELEVANT


# ── serialisation ────────────────────────────────────────────────────────────

def test_to_dict_round_trips_shape():
    rep = check_consistency(
        [DecidedCase("a", {"harm": "yes", "hair": "red"}, "liable"),
         DecidedCase("b", {"harm": "yes", "hair": "blue"}, "not-liable")],
        relevant_keys={"harm"},
    )
    d = rep.to_dict()
    assert d["consistent"] is False
    assert d["pairs"][0]["kind"] == IRRELEVANT
    assert d["pairs"][0]["differing_keys"] == ["hair"]
    assert isinstance(rep, ConsistencyReport)
    assert isinstance(rep.pairs[0], InconsistentPair)
