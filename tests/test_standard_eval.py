# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Standard evaluation (O-STD): a model proposes a benchmark, the facts it
relies on and a met/not-met verdict; deterministic gates decide. These tests
drive a fixed :class:`StubModel` and assert the GATES fire — ANSWER a
grounded/high-confidence application (SATISFIED when met, NOT_SATISFIED when
not), REJECT an invented benchmark or fact, ESCALATE a genuinely-contested
application, an unsound decomposition and sub-floor confidence — and that no
confident verdict is ever returned on an ungrounded benchmark or a contested
call. Escalation is a pass. Outcomes are asserted only by the status/gate that
fired, never by re-deriving the model's answer."""
from __future__ import annotations

from loomground_solver.standard_eval import (
    evaluate_standard, StubModel, StandardResult,
)


# ── canned facts + proposals (fixed; the StubModel returns these verbatim) ─────

# Good faith: the benchmark span and both relied-fact spans are verbatim
# substrings of the facts text, and confidences sit above the floor.
GOOD_FAITH_FACTS = (
    "Good faith required the seller to disclose the flooding history. "
    "The seller knew the basement had flooded twice and said nothing "
    "before the sale."
)

MET = {
    "benchmark": {"span": "Good faith required the seller to disclose the "
                          "flooding history",
                  "literal": "benchmark:disclose-flooding", "confidence": 0.96},
    "relied_on": [
        {"span": "The seller knew the basement had flooded twice",
         "literal": "knew-flooding", "confidence": 0.95},
        {"span": "said nothing", "literal": "concealed", "confidence": 0.93},
    ],
    "verdict": {"span": "", "literal": "verdict:breached", "confidence": 0.92},
    "met": True,
}

# Reasonable person, clearly NOT breached: benchmark met, verdict met=False.
REASONABLE_FACTS = (
    "A reasonable driver would slow near the crossing. "
    "The driver slowed to 15 and stopped when the child stepped out."
)

NOT_MET = {
    "benchmark": {"span": "A reasonable driver would slow near the crossing",
                  "literal": "benchmark:slow-near-crossing", "confidence": 0.94},
    "relied_on": [
        {"span": "The driver slowed to 15", "literal": "slowed",
         "confidence": 0.93},
        {"span": "stopped when the child stepped out", "literal": "stopped",
         "confidence": 0.9},
    ],
    "verdict": {"span": "", "literal": "verdict:no-breach", "confidence": 0.91},
    "met": False,
}

# An invented benchmark: the span is nowhere in GOOD_FAITH_FACTS.
UNGROUNDED_BENCHMARK = {
    "benchmark": {"span": "a reasonable android would teleport the buyer to safety",
                  "literal": "benchmark:teleport", "confidence": 0.97},
    "relied_on": [
        {"span": "said nothing", "literal": "concealed", "confidence": 0.95},
    ],
    "verdict": {"span": "", "literal": "verdict:breached", "confidence": 0.95},
    "met": True,
}

# A grounded benchmark but an invented relied-on fact.
UNGROUNDED_FACT = {
    "benchmark": {"span": "Good faith required the seller to disclose the "
                          "flooding history",
                  "literal": "benchmark:disclose-flooding", "confidence": 0.96},
    "relied_on": [
        {"span": "the seller wired the buyer a bribe of ten thousand dollars",
         "literal": "bribe", "confidence": 0.95},
    ],
    "verdict": {"span": "", "literal": "verdict:breached", "confidence": 0.95},
    "met": True,
}

# Grounded and confident, but the model itself flags the call as one reasonable
# people could decide either way.
CONTESTED = {
    "benchmark": {"span": "Good faith required the seller to disclose the "
                          "flooding history",
                  "literal": "benchmark:disclose-flooding", "confidence": 0.96},
    "relied_on": [
        {"span": "The seller knew the basement had flooded twice",
         "literal": "knew-flooding", "confidence": 0.95},
    ],
    "verdict": {"span": "", "literal": "verdict:breached", "confidence": 0.95},
    "met": True,
    "contested": True,
}

# Grounded and non-contested, but a relied fact confidence sits below the floor.
SUB_FLOOR = {
    "benchmark": {"span": "Good faith required the seller to disclose the "
                          "flooding history",
                  "literal": "benchmark:disclose-flooding", "confidence": 0.96},
    "relied_on": [
        {"span": "said nothing", "literal": "concealed", "confidence": 0.40},
    ],
    "verdict": {"span": "", "literal": "verdict:breached", "confidence": 0.95},
    "met": True,
}

# A self-contradictory set of relied facts: 'disclosed' and its negation, both
# grounded — the auditor must catch the incoherent application.
CONTRA_FACTS = (
    "The seller disclosed the defect in the email but later "
    "the seller did not disclose the defect at closing."
)

AUDIT_UNSOUND = {
    "benchmark": {"span": "disclose the defect at closing",
                  "literal": "benchmark:disclose", "confidence": 0.95},
    "relied_on": [
        {"span": "The seller disclosed the defect in the email",
         "literal": "disclosed", "confidence": 0.95},
        {"span": "the seller did not disclose the defect at closing",
         "literal": "-disclosed", "confidence": 0.95},
    ],
    "verdict": {"span": "", "literal": "verdict:breached", "confidence": 0.95},
    "met": True,
}

# Malformed: no benchmark at all.
MALFORMED = {
    "relied_on": [
        {"span": "said nothing", "literal": "concealed", "confidence": 0.95},
    ],
    "verdict": {"span": "", "literal": "verdict:breached", "confidence": 0.95},
    "met": True,
}


# ── the tests: one gate/branch per case ───────────────────────────────────────

def test_clear_met_is_satisfied():
    """A grounded, non-contested, high-confidence application whose benchmark is
    met → SATISFIED, with the benchmark literal reported."""
    res = evaluate_standard("good faith", GOOD_FAITH_FACTS, model=StubModel(MET))
    assert isinstance(res, StandardResult)
    assert res.status == "satisfied"
    assert res.satisfied and not res.escalated
    assert res.verdict is True
    assert res.benchmark == "benchmark:disclose-flooding"
    assert res.gate_report["answered"] is True


def test_clear_unmet_is_not_satisfied():
    """The same machinery, benchmark NOT met → NOT_SATISFIED (a grounded 'no',
    not an escalation)."""
    res = evaluate_standard("reasonable person", REASONABLE_FACTS,
                            model=StubModel(NOT_MET))
    assert res.status == "not_satisfied"
    assert res.not_satisfied and not res.escalated
    assert res.verdict is False


def test_ungrounded_benchmark_is_rejected():
    """The benchmark span is not in the facts → REJECT as invented; no verdict."""
    res = evaluate_standard("good faith", GOOD_FAITH_FACTS,
                            model=StubModel(UNGROUNDED_BENCHMARK))
    assert res.status == "rejected"
    assert res.rejected and res.verdict is None and not res.escalated
    assert res.gate_report["grounding"]["ok"] is False
    assert res.gate_report["grounding"]["invented"]


def test_ungrounded_relied_fact_is_rejected():
    """A grounded benchmark cannot rescue an invented relied-on fact → REJECT."""
    res = evaluate_standard("good faith", GOOD_FAITH_FACTS,
                            model=StubModel(UNGROUNDED_FACT))
    assert res.status == "rejected"
    assert res.gate_report["grounding"]["ok"] is False


def test_genuinely_contested_escalates():
    """A grounded, confident application the model flags as contested is a human's
    call → ESCALATE, never a confident verdict. Escalation is a PASS."""
    res = evaluate_standard("good faith", GOOD_FAITH_FACTS,
                            model=StubModel(CONTESTED))
    assert res.status == "escalated"
    assert res.escalated and res.verdict is None
    assert res.gate_report["contested"]["contested"] is True
    # It never ran a confident verdict past the contested flag.
    assert "answered" not in res.gate_report


def test_audit_unsound_escalates():
    """Contradictory relied facts ('disclosed' and its negation) make the
    decomposition unsound → ESCALATE (the solver catching an incoherent
    application), regardless of the high self-reported confidence."""
    res = evaluate_standard("good faith", CONTRA_FACTS,
                            model=StubModel(AUDIT_UNSOUND))
    assert res.status == "escalated"
    assert res.escalated
    assert res.gate_report["audit"]["verdict"] == "unsound"


def test_sub_floor_confidence_escalates():
    """A grounded, non-contested, sound application with a sub-floor relied-fact
    confidence → ESCALATE. Confidence is never trusted alone, and a low score is
    never bought past by the high ones."""
    res = evaluate_standard("good faith", GOOD_FAITH_FACTS,
                            model=StubModel(SUB_FLOOR))
    assert res.status == "escalated"
    assert res.escalated
    assert res.gate_report["confidence"]["ok"] is False


def test_malformed_proposal_is_rejected():
    """A proposal with no benchmark is malformed → REJECT (nothing to ground)."""
    res = evaluate_standard("good faith", GOOD_FAITH_FACTS,
                            model=StubModel(MALFORMED))
    assert res.status == "rejected"
    assert res.gate_report["wellformed"]["ok"] is False


def test_never_answers_on_ungrounded_or_contested():
    """Cross-cutting invariant: for every non-answer input, the result never
    carries a concrete verdict and never claims to have answered."""
    for payload in (UNGROUNDED_BENCHMARK, UNGROUNDED_FACT, CONTESTED,
                    SUB_FLOOR, MALFORMED):
        res = evaluate_standard("good faith", GOOD_FAITH_FACTS,
                                model=StubModel(payload))
        assert res.status in ("rejected", "escalated")
        assert res.verdict is None
        assert "answered" not in res.gate_report
