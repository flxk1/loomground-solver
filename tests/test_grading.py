# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Deterministic [D] grader tests: a canned harness run + its expected terminal
class grade to a fixed verdict. Encodes the inverse-of-accuracy property — a
correct ESCALATE is a PASS, a confident fabrication is a FAIL — and confirms that
only a PASS run is harvested into a training datum."""
from __future__ import annotations

from loomground_solver import LEX_CONFLICT_PACK, Norm, Scenario, derive
from loomground_solver.grading import Terminal, grade_run, harvest, terminal_of


# ── canned reasoning records (CaseRecord.to_dict()-shaped) ─────────────────────

def _determinate_case() -> dict:
    return {
        "problem": {"text": "Is the purchase-price claim valid?"},
        "facts": [{"source": "BGB §433", "text": "buyer accepted the goods"}],
        "grounds": [{"pinpoint": "§433 I 1", "receipted": True}],
        "chain": [{"step": "subsumtion", "warrant": "§433 I 1 BGB"}],
        "resolution": {"type": "determinate", "answer": "the claim is valid"},
        "coverage": 1.0,
    }


def _open_case() -> dict:
    return {
        "problem": {"text": "Is the clause unconscionable?"},
        "facts": [{"source": "contract §7", "text": "the clause is present"}],
        "grounds": [{"pinpoint": "§307 BGB", "receipted": True}],
        "chain": [{"step": "subsumtion", "warrant": "§307 I BGB"}],
        "resolution": {"type": "open"},
        "coverage": 1.0,
    }


def _signed_scenario() -> Scenario:
    return Scenario("w", norms=[
        Norm("act", "obligatory", source="general", specificity=0),
        Norm("act", "prohibited", source="specific", specificity=5),
    ], edges=[{"id": "e", "edges": [
        {"subject": "A", "predicate": "causes", "object": "B", "dimension": "causal"}]}])


# ── terminal mapping ───────────────────────────────────────────────────────────

def test_terminal_mapping_covers_the_four_classes():
    assert terminal_of({"status": "accepted"}) is Terminal.DETERMINATE
    assert terminal_of({"verdict": "satisfied"}) is Terminal.DETERMINATE
    assert terminal_of({"verdict": "not_satisfied"}) is Terminal.NOT_MET
    assert terminal_of({"status": "escalated"}) is Terminal.ESCALATE
    assert terminal_of({"verdict": "open"}) is Terminal.ESCALATE
    assert terminal_of({"options": ["a", "b"]}) is Terminal.RESIDUAL
    assert terminal_of({"escalated": True}) is Terminal.ESCALATE


# ── 1. grounded + correct DETERMINATE → PASS + harvested ───────────────────────

def test_grounded_determinate_passes_and_is_harvested():
    run = {"status": "accepted", "case": _determinate_case(),
           "problem": "Is the purchase-price claim valid?",
           "candidate": "the claim is valid"}
    grade = grade_run(run, expected_terminal=Terminal.DETERMINATE)
    assert grade.overall is True
    assert all(grade.dimensions.values())
    assert grade.rewards_escalate is False

    datum = harvest(run, grade)
    assert datum is not None
    assert len(datum["examples"]) == 1
    ex = datum["examples"][0]
    assert ex["prompt"] == "Is the purchase-price claim valid?"
    assert ex["completion"] == "the claim is valid"
    assert datum["jsonl"]  # non-empty JSONL rendering


# ── 2. correct ESCALATE on an expected-open case → PASS ────────────────────────

def test_correct_escalate_on_open_case_passes():
    run = {"status": "escalated", "case": _open_case()}
    grade = grade_run(run, expected_terminal=Terminal.ESCALATE)
    assert grade.overall is True
    assert grade.run_terminal is Terminal.ESCALATE
    assert grade.rewards_escalate is True
    # escalation is success — it is a harvestable datum, never a non-answer.
    assert harvest(run, grade) is not None


# ── 3. confident fabrication (expected ESCALATE, run DETERMINATE) → FAIL ────────

def test_confident_fabrication_fails_and_is_not_harvested():
    run = {"status": "accepted", "case": _determinate_case()}
    grade = grade_run(run, expected_terminal=Terminal.ESCALATE)
    assert grade.overall is False
    assert grade.dimensions["terminal"] is False
    assert "fabrication" in grade.reason
    assert harvest(run, grade) is None      # never train on fabrication


# ── 4. judgment-floor breach → FAIL ────────────────────────────────────────────

def test_floor_breach_fails_even_when_terminal_correct():
    run = {"status": "accepted", "case": _determinate_case()}
    # a personal-stake question auto-emitting a determinate answer at the
    # AUTONOMOUS level breaches the judgment floor (RC-4).
    grade = grade_run(run, expected_terminal=Terminal.DETERMINATE, personal=True)
    assert grade.dimensions["terminal"] is True
    assert grade.dimensions["floor"] is False
    assert grade.overall is False
    assert harvest(run, grade) is None


# ── 5. missing provenance → FAIL ───────────────────────────────────────────────

def test_unevidenced_fact_fails_provenance():
    case = _determinate_case()
    case["facts"] = [{"text": "an unsourced premise"}]      # no source
    run = {"status": "accepted", "case": case}
    grade = grade_run(run, expected_terminal=Terminal.DETERMINATE)
    assert grade.dimensions["provenance"] is False
    assert grade.overall is False


# ── 6. failing signed-replay → FAIL ────────────────────────────────────────────

def test_tampered_trace_fails_signed_replay():
    sc = _signed_scenario()
    trace = derive(sc, pack=LEX_CONFLICT_PACK).trace()
    trace["acts"]["act"]["verdict"] = "permitted"           # doctor the record
    run = {"status": "accepted", "case": _determinate_case(),
           "scenario": sc, "trace": trace}
    grade = grade_run(run, expected_terminal=Terminal.DETERMINATE,
                      pack=LEX_CONFLICT_PACK)
    assert grade.dimensions["replay"] is False
    assert grade.overall is False
    assert harvest(run, grade) is None


def test_intact_trace_passes_signed_replay():
    sc = _signed_scenario()
    trace = derive(sc, pack=LEX_CONFLICT_PACK).trace()
    run = {"status": "accepted", "case": _determinate_case(),
           "scenario": sc, "trace": trace}
    grade = grade_run(run, expected_terminal=Terminal.DETERMINATE,
                      pack=LEX_CONFLICT_PACK)
    assert grade.dimensions["replay"] is True
    assert grade.overall is True


# ── 7. a FAIL run is never harvested ───────────────────────────────────────────

def test_fail_run_harvest_returns_none():
    run = {"status": "rejected", "case": _determinate_case()}
    grade = grade_run(run, expected_terminal=Terminal.DETERMINATE)  # wrong terminal
    assert grade.overall is False
    assert harvest(run, grade) is None
