# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Auslegung (O36–O45) — per-element interpretation via the canons.

These tests assert the GATES and the BRANCHES, not a fixed reading for the hard
cases: converge → reading; diverge + tie-breaker settles → reading via the
tie-breaking canon; diverge unsettled → ESCALATE; a reading crossing the wording
cap → ESCALATE (contra legem); sub-floor confidence → ESCALATE; a settled reading
→ short-circuit (model never called). Escalation is a PASS: the op declining to
answer a genuinely open call is the correct outcome, not a failure.

The model is always a deterministic :class:`StubModel` returning canned per-canon
fills in the interpret notation — never a real LLM.
"""
from __future__ import annotations

from loomground_solver.auslegung import (
    ReadingResult, StubModel, interpret_element,
)

ELEMENT = "Schriftform"
TEXT = "The declaration requires Schriftform to be effective."


def _fill(reading: str, span: str = "wording", conf: float = 0.95,
          *, extra_readings: tuple[str, ...] = ()) -> str:
    """One canon's fill: ground ``reading`` (and any ``extra_readings`` the same
    span also admits — used to widen the grammatical canon's wording-admissible
    set) to ``span`` in the interpret notation, at confidence ``conf``."""
    lines = [f"fact: {span}"]
    for r in (reading, *extra_readings):
        lines.append(f"rule: {span} => {r}")
    lines.append(f"claim: {reading}")
    lines.append(f"conf: {conf}")
    return "\n".join(lines)


# ── (b) O36 — a settled reading short-circuits and never calls the model ─────

def test_settled_reading_short_circuits_and_skips_the_model():
    model = StubModel({})  # empty: if consulted, every canon reads as nothing
    res = interpret_element(ELEMENT, TEXT, model=model,
                            settled="written form", family="civil-law")
    assert isinstance(res, ReadingResult)
    assert res.escalated is False
    assert res.reading == "written form"
    assert res.tiebreaker_used is False
    assert res.canon_readings == {}
    assert model.calls == []          # O36: the model was never consulted


# ── (e) O45 — canons converge → the synthesised reading ──────────────────────

def test_convergent_canons_yield_synthesised_reading():
    fill = _fill("a written document")
    model = StubModel({c: fill for c in
                       ("grammatical", "systematic", "historical", "teleological")})
    res = interpret_element(ELEMENT, TEXT, model=model, family="civil-law")
    assert res.escalated is False
    assert res.reading == "a written document"
    assert res.tiebreaker_used is False
    assert "converge" in res.reason.lower()
    assert all(r["status"] == "ok" for r in res.canon_readings.values())


# ── (f) O44 — canons diverge, the tie-breaker settles → tie-breaker reading ──

def test_divergence_settled_by_tiebreaker_returns_teleological_reading():
    # Grammatical wording admits BOTH "a written document" and "a written notice"
    # (its span grounds both), so the teleological reading stays within the cap.
    grammatical = _fill("a written document",
                        extra_readings=("a written notice",))
    systematic = _fill("an electronic record", span="system-context")
    historical = _fill("a written document")
    teleological = _fill("a written notice", span="purpose-of-form")
    model = StubModel({
        "grammatical": grammatical, "systematic": systematic,
        "historical": historical, "teleological": teleological,
    })
    res = interpret_element(ELEMENT, TEXT, model=model, family="civil-law")
    assert res.escalated is False
    assert res.tiebreaker_used is True                 # settled by the tie-breaker
    # civil-law tie-breaker is teleological; its reading wins, and it is within
    # the grammatical wording cap.
    assert res.reading == "a written notice"
    assert "teleological" in res.reason.lower()


# ── (h) O48 — canons diverge, tie-breaker unavailable → ESCALATE (open) ──────

def test_divergence_unsettled_by_missing_tiebreaker_escalates():
    # Two surviving readings diverge, but the tie-breaking canon (teleological)
    # produced NO gated reading (empty fill → ungrounded → dropped), so the
    # family's own instrument for settling the tie is unavailable.
    model = StubModel({
        "grammatical": _fill("a written document"),
        "systematic": _fill("an electronic record", span="system-context"),
        "historical": _fill("a written document"),
        "teleological": "",     # no reading → dropped
    })
    res = interpret_element(ELEMENT, TEXT, model=model, family="civil-law")
    assert res.escalated is True            # ESCALATION IS A PASS
    assert res.reading is None
    assert res.canon_readings["teleological"]["status"] == "ungrounded"
    assert "unsettled" in res.reason.lower() or "O48" in res.reason


# ── (g) O37 — a reading the wording cannot bear → ESCALATE (contra legem) ─────

def test_reading_crossing_wortlautgrenze_escalates_contra_legem():
    # Grammatical wording admits only "a written statement"; the teleological
    # (tie-breaker) reading "an oral statement" is outside that wording. The
    # tie-breaker would pick it, but the Wortlautgrenze forbids returning it.
    model = StubModel({
        "grammatical": _fill("a written statement"),
        "systematic": _fill("a written statement"),
        "historical": _fill("a written statement"),
        "teleological": _fill("an oral statement", span="purpose-of-form"),
    })
    res = interpret_element(ELEMENT, TEXT, model=model, family="civil-law")
    assert res.escalated is True            # never returns the crossing reading
    assert res.reading is None
    # the crossing reading was itself gate-clean — it is the CAP that stops it,
    # not a failed fill:
    assert res.canon_readings["teleological"]["status"] == "ok"
    assert ("wortlautgrenze" in res.reason.lower()
            or "contra legem" in res.reason.lower())


# ── confidence never trusted alone: sub-floor → ESCALATE ─────────────────────

def test_sub_floor_confidence_escalates_even_when_canons_agree():
    # Every canon agrees on the reading, but each is below the contract's
    # confidence floor (0.85) → no reading survives the gate → escalate.
    fill = _fill("a written document", conf=0.40)
    model = StubModel({c: fill for c in
                       ("grammatical", "systematic", "historical", "teleological")})
    res = interpret_element(ELEMENT, TEXT, model=model, family="civil-law",
                            risk_class="C")
    assert res.escalated is True
    assert res.reading is None
    assert all(r["status"] == "sub-floor" for r in res.canon_readings.values())
    assert "confidence floor" in res.reason.lower()


# ── the audit gate drops an ungrounded reading without derailing convergence ──

def test_ungrounded_reading_is_dropped_by_audit_but_others_converge():
    # Systematic claims a reading with NO grounding span (claim only) — the
    # interpret.audit gate catches the leap and drops it. The remaining canons
    # converge, so the op still returns a reading.
    ungrounded = "claim: a smuggled reading\nconf: 0.95"   # no fact, no rule
    grounded = _fill("a written document")
    model = StubModel({
        "grammatical": grounded, "systematic": ungrounded,
        "historical": grounded, "teleological": grounded,
    })
    res = interpret_element(ELEMENT, TEXT, model=model, family="civil-law")
    assert res.escalated is False
    assert res.reading == "a written document"
    assert res.canon_readings["systematic"]["status"] == "ungrounded"


# ── no cap in the tradition (common-law) → the tie-breaker reading stands ─────

def test_common_law_has_no_wording_cap_so_tiebreaker_reading_stands():
    # Common-law recognises no single wording cap (CanonSet.cap == ""). Canons
    # diverge; the tie-breaker (purpose) wins, and NO Wortlautgrenze can block
    # it — a reading that would be "beyond wording" is not contra legem where the
    # tradition has no such outer limit.
    model = StubModel({
        "ordinary-meaning": _fill("the ordinary sense", span="ordinary"),
        "noscitur-a-sociis": _fill("the neighbour sense", span="neighbours"),
        "ejusdem-generis": _fill("the class sense", span="class"),
        "expressio-unius": _fill("the exclusion sense", span="listing"),
        "purpose": _fill("the purposive sense", span="purpose"),
    })
    res = interpret_element(ELEMENT, TEXT, model=model, family="common-law")
    assert res.escalated is False
    assert res.tiebreaker_used is True
    assert res.reading == "the purposive sense"          # purpose breaks the tie
    assert res.provenance["cap"] == ""                   # no outer cap exists
