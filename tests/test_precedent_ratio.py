# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Precedent ratio extraction (O143): the model separates ratio from obiter, the
contract gates, the harness escalates the genuinely contestable.

These tests drive a deterministic :class:`StubModel` (a canned case reading) and
assert the GATES and the BRANCHES — a clean ratio lowers to a Rule with the obiter
EXCLUDED; an ungrounded material fact is REJECTED; a ratio element the holding did
not need is FLAGGED; multiple/unclear candidate ratios ESCALATE; a missing binding
ground (warrant) ESCALATES; a self-contradictory reading ESCALATES; sub-floor
confidence ESCALATES. Escalation is a PASS. For the hard cases we assert the
verdict and structure, never a fixed Rule equality."""
from __future__ import annotations

from loomground_solver.precedent_ratio import (
    RatioResult,
    StubModel,
    extract_ratio,
)


# A single coherent case-text. Every canned span below is a substring of it (or,
# for the grounding test, deliberately is not).
CASE = (
    "The defendant, a courier, left a parcel unattended on the doorstep of an "
    "empty house. The parcel was stolen before the consignee returned. "
    "The court held that a carrier who leaves goods unattended in a public place "
    "breaches the duty of care owed to the consignee and is liable for the loss. "
    "The court observed, in passing, that liability might differ for registered "
    "mail, though that question did not arise on these facts."
)


def _clean_reading() -> dict:
    """A well-formed reading: two necessary material facts, a holding, one obiter
    remark kept apart. All spans are substrings of CASE."""
    return {
        "ratio_statement": "a carrier who leaves goods unattended in a public "
                           "place is liable for the loss",
        "material_facts": [
            {"span": "left a parcel unattended", "literal": "goods_left_unattended",
             "confidence": 0.95, "necessary": True},
            {"span": "in a public place", "literal": "public_place",
             "confidence": 0.9, "necessary": True},
        ],
        "holding": {"span": "is liable for the loss", "literal": "carrier_liable",
                    "confidence": 0.93},
        "obiter": [
            {"span": "liability might differ for registered mail",
             "literal": "registered_mail_differs", "confidence": 0.6},
        ],
    }


# ── clean ratio → a Rule, with the obiter EXCLUDED ────────────────────────────

def test_clean_ratio_lowers_to_rule_and_excludes_obiter():
    res = extract_ratio(CASE, model=StubModel(_clean_reading()),
                        court="BGH", level="appellate")
    assert isinstance(res, RatioResult)
    assert res.extracted and not res.escalated
    assert res.rule is not None
    # the ratio's operative conditions are the NECESSARY material facts
    assert set(res.rule.conditions) == {"goods_left_unattended", "public_place"}
    assert res.rule.consequence == "carrier_liable"
    assert res.rule.source == "BGH / appellate"
    # obiter is carried, but SEPARATELY — never inside the Rule
    assert len(res.obiter) == 1
    assert res.obiter[0]["literal"] == "registered_mail_differs"
    assert "registered_mail_differs" not in res.rule.conditions
    assert "registered_mail_differs" != res.rule.consequence
    # every material fact in the Rule is span-grounded
    assert all(r["grounded"] for r in res.material_facts)


# ── obiter is never a source of Rule content ──────────────────────────────────

def test_obiter_is_kept_separate_from_the_rule():
    res = extract_ratio(CASE, model=StubModel(_clean_reading()))
    assert res.extracted
    obiter_lits = {o["literal"] for o in res.obiter}
    rule_lits = set(res.rule.conditions) | {res.rule.consequence}
    assert obiter_lits.isdisjoint(rule_lits)


# ── ungrounded material fact → REJECT (invented, not in the case-text) ─────────

def test_ungrounded_material_fact_is_rejected():
    reading = _clean_reading()
    reading["material_facts"].append(
        {"span": "left a bicycle unlocked outside a bank",  # NOT in CASE
         "literal": "bicycle_unlocked", "confidence": 0.99, "necessary": True})
    res = extract_ratio(CASE, model=StubModel(reading))
    assert res.rejected
    assert res.rule is None
    assert not res.escalated
    assert not res.gate_report["grounding"]["ok"]
    assert "left a bicycle unlocked outside a bank" in res.gate_report["grounding"]["invented"]


# ── ratio element NOT necessary to the holding → FLAGGED, excluded from the Rule ─

def test_unnecessary_ratio_element_is_flagged_not_kept():
    reading = _clean_reading()
    # a material fact the holding did not need — placed in the ratio, flagged out
    reading["material_facts"].append(
        {"span": "empty house", "literal": "house_was_empty",
         "confidence": 0.9, "necessary": False})
    res = extract_ratio(CASE, model=StubModel(reading))
    assert res.extracted            # still a determinable ratio
    assert res.rule is not None
    # the unnecessary element is FLAGGED, and kept OUT of the binding Rule
    assert any(f["literal"] == "house_was_empty" for f in res.flagged)
    assert "house_was_empty" not in res.rule.conditions
    assert res.rule.consequence != "house_was_empty"


# ── multiple defensible candidate ratios → ESCALATE (never fabricate one) ──────

def test_multiple_candidate_ratios_escalate():
    reading = _clean_reading()
    reading["candidate_ratios"] = [
        "a carrier is liable for goods left unattended in public",
        "a carrier is liable only for goods of declared value",
    ]
    res = extract_ratio(CASE, model=StubModel(reading))
    assert res.escalated
    assert res.rule is None
    assert not res.gate_report["contestability"]["ok"]
    assert "contestable" in res.reason


# ── an unclear ratio → ESCALATE ───────────────────────────────────────────────

def test_unclear_ratio_escalates():
    reading = _clean_reading()
    reading["ratio_unclear"] = True
    res = extract_ratio(CASE, model=StubModel(reading))
    assert res.escalated
    assert res.rule is None
    assert res.gate_report["contestability"]["unclear"] is True


# ── missing binding ground (no warrant) → ESCALATE (R2) ───────────────────────

def test_ratio_without_a_stated_binding_ground_escalates():
    reading = _clean_reading()
    reading["ratio_statement"] = ""   # no warrant for the move
    res = extract_ratio(CASE, model=StubModel(reading))
    assert res.escalated
    assert res.rule is None
    assert res.gate_report["warrant"]["escalate"] is True


# ── a self-contradictory reading → ESCALATE (audit unsound) ───────────────────

def test_self_contradictory_reading_escalates_on_audit():
    reading = _clean_reading()
    # a material fact whose literal negates the holding → inconsistent closure
    reading["material_facts"].append(
        {"span": "did not arise on these facts", "literal": "-carrier_liable",
         "confidence": 0.95, "necessary": True})
    res = extract_ratio(CASE, model=StubModel(reading))
    assert res.escalated
    assert res.rule is None
    assert res.gate_report["audit"]["verdict"] == "unsound"


# ── sub-floor confidence → ESCALATE (confidence never trusted alone) ──────────

def test_sub_floor_confidence_escalates():
    reading = _clean_reading()
    reading["material_facts"][0]["confidence"] = 0.4   # below the 0.85 floor
    res = extract_ratio(CASE, model=StubModel(reading), risk_class="C")
    assert res.escalated
    assert res.rule is None
    assert not res.gate_report["confidence"]["ok"]


# ── the stub is a genuine ModelFn (str -> str) ────────────────────────────────

def test_stub_model_is_a_modelfn():
    model = StubModel(_clean_reading())
    out = model("any prompt at all")
    assert isinstance(out, str) and out.strip().startswith("{")
