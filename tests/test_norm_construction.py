# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Norm construction (O26): a model proposes a decomposition of a norm-text,
deterministic gates decide. These tests drive a fixed :class:`StubModel` and
assert the GATES fire — accept a grounded/faithful/high-confidence proposal,
REJECT an invented span, FLAG a dropped clause, ESCALATE on sub-floor
confidence, an unsound decomposition and a discretionary modality — and that no
ungrounded Rule is ever returned. Escalation is a pass. Outputs are never
asserted by Rule-equality; only the gate that fired is."""
from __future__ import annotations

from loomground_solver.norm_construction import (
    construct_norm, StubModel, ConstructionResult,
)
from loomground_solver.subsumption import Rule


# ── canned proposals (fixed; the StubModel returns these verbatim) ────────────

# A clean deontic norm: every span below is a verbatim substring of TEXT_ERASE,
# and the four spans together cover its operative content.
TEXT_ERASE = "the controller shall erase personal data unless consent was withdrawn"

GROUNDED_FAITHFUL = {
    "elements": [
        {"span": "the controller", "literal": "controller", "confidence": 0.97},
        {"span": "personal data", "literal": "personal-data", "confidence": 0.95},
    ],
    "consequence": {"span": "shall erase personal data", "literal": "O:erase",
                    "confidence": 0.96},
    "exceptions": [
        {"span": "unless consent was withdrawn", "literal": "consent-withdrawn",
         "confidence": 0.93},
    ],
    "modality": "obligatory",
    "act": "erase",
}

# An invented element: the span is nowhere in TEXT_ERASE.
UNGROUNDED = {
    "elements": [
        {"span": "the controller", "literal": "controller", "confidence": 0.97},
        {"span": "the processor shall notify the authority",   # not in the text
         "literal": "notify", "confidence": 0.99},
    ],
    "consequence": {"span": "shall erase personal data", "literal": "O:erase",
                    "confidence": 0.96},
    "modality": "obligatory",
}

# Drops the operative exception clause and does not flag it (NT-5 / coverage).
DROPS_EXCEPTION = {
    "elements": [
        {"span": "the controller", "literal": "controller", "confidence": 0.97},
        {"span": "personal data", "literal": "personal-data", "confidence": 0.95},
    ],
    "consequence": {"span": "shall erase personal data", "literal": "O:erase",
                    "confidence": 0.96},
    "exceptions": [],                       # the "unless…" clause is absorbed
    "modality": "obligatory",
}

# Grounded + faithful, but the weakest span is far below the floor.
SUB_FLOOR = {
    "elements": [
        {"span": "the controller", "literal": "controller", "confidence": 0.40},
        {"span": "personal data", "literal": "personal-data", "confidence": 0.95},
    ],
    "consequence": {"span": "shall erase personal data", "literal": "O:erase",
                    "confidence": 0.92},
    "exceptions": [
        {"span": "unless consent was withdrawn", "literal": "consent-withdrawn",
         "confidence": 0.93},
    ],
    "modality": "obligatory",
}

# A self-contradictory Tatbestand, proposed with very high confidence. Every
# span is grounded and the spans cover the operative content, so the proposal
# reaches the audit gate — which finds it inconsistent.
TEXT_SWITCH = "the switch is active but the switch is not active"
INCONSISTENT_HIGH_CONF = {
    "elements": [
        {"span": "the switch is active", "literal": "active", "confidence": 0.99},
        {"span": "is not active", "literal": "-active", "confidence": 0.99},
    ],
    "consequence": {"span": "the switch is active", "literal": "state:on",
                    "confidence": 0.99},
    "modality": "",
}

# Grounded + faithful + sound, but a discretionary modality (NT-4).
TEXT_WAIVE = "the authority may waive the fee"
DISCRETIONARY = {
    "elements": [
        {"span": "the authority", "literal": "authority-competent",
         "confidence": 0.95},
    ],
    "consequence": {"span": "may waive the fee", "literal": "P:waive",
                    "confidence": 0.95},
    "modality": "may",
    "modal_phrase": "may",
    "act": "waive",
}


# ── the gates ─────────────────────────────────────────────────────────────────

def test_grounded_faithful_high_conf_is_accepted():
    res = construct_norm(TEXT_ERASE, model=StubModel(GROUNDED_FAITHFUL),
                         locus="Art. 17(1)")
    assert isinstance(res, ConstructionResult)
    assert res.accepted and not res.escalated
    assert isinstance(res.rule, Rule)
    # the accepted Rule is grounded: every receipt is anchored in the text.
    assert res.gate_report["grounding"]["ok"] is True
    assert all(r["grounded"] for r in res.provenance["receipts"])
    assert res.rule.source == "Art. 17(1)"
    # the exception was carried, not absorbed.
    assert res.rule.exceptions == ("consent-withdrawn",)


def test_ungrounded_element_is_rejected_never_returns_a_rule():
    res = construct_norm(TEXT_ERASE, model=StubModel(UNGROUNDED))
    assert res.rejected and res.rule is None            # honesty floor #1/#3
    assert not res.escalated                            # a reject, not a defer
    assert res.gate_report["grounding"]["ok"] is False
    assert any("processor shall notify" in s
               for s in res.gate_report["grounding"]["invented"])


def test_dropped_operative_clause_is_flagged():
    res = construct_norm(TEXT_ERASE, model=StubModel(DROPS_EXCEPTION))
    assert not res.accepted and res.rule is None
    faith = res.gate_report["faithfulness"]
    assert faith["ok"] is False                         # span-coverage failed
    # the dropped "unless … withdrawn" words are reported as uncovered.
    assert {"unless", "consent", "withdrawn"} <= set(faith["uncovered"])


def test_sub_floor_confidence_escalates():
    res = construct_norm(TEXT_ERASE, model=StubModel(SUB_FLOOR))
    assert res.escalated and res.rule is None           # escalation is a pass
    assert res.gate_report["confidence"]["ok"] is False
    assert res.gate_report["confidence"]["min"] < res.gate_report["confidence"]["floor"]


def test_inconsistent_decomposition_escalates_despite_high_confidence():
    # honesty floor #2: a 0.99-confidence proposal that is internally
    # contradictory does not buy its way to an acceptance — the audit gate fires.
    res = construct_norm(TEXT_SWITCH, model=StubModel(INCONSISTENT_HIGH_CONF))
    assert res.escalated and res.rule is None
    assert res.gate_report["audit"]["verdict"] == "unsound"
    # confidence never even got to overrule the audit.
    assert "confidence" not in res.gate_report


def test_discretionary_modality_escalates():
    res = construct_norm(TEXT_WAIVE, model=StubModel(DISCRETIONARY),
                         locus="§ 227 AO")
    assert res.escalated and res.rule is None
    assert res.gate_report["deontic"]["escalate"] is True


def test_no_ungrounded_rule_is_ever_returned():
    # Across every failing shape, the invariant holds: rule is None whenever the
    # construction did not accept, and an accepted rule is always grounded.
    cases = [
        (TEXT_ERASE, UNGROUNDED),
        (TEXT_ERASE, DROPS_EXCEPTION),
        (TEXT_ERASE, SUB_FLOOR),
        (TEXT_SWITCH, INCONSISTENT_HIGH_CONF),
        (TEXT_WAIVE, DISCRETIONARY),
    ]
    for text, proposal in cases:
        res = construct_norm(text, model=StubModel(proposal))
        assert not res.accepted
        assert res.rule is None
    ok = construct_norm(TEXT_ERASE, model=StubModel(GROUNDED_FAITHFUL))
    assert ok.accepted and ok.rule is not None
    assert all(r["grounded"] for r in ok.provenance["receipts"])


def test_stub_model_is_a_str_to_str_modelfn_and_deterministic():
    # The fill seam is ports.ModelFn (str -> str): the stub returns a string
    # completion, stable across calls, that construct_norm decodes.
    model = StubModel(GROUNDED_FAITHFUL)
    out1 = model("any prompt")
    out2 = model("a different prompt")
    assert isinstance(out1, str) and out1 == out2       # deterministic
    res = construct_norm(TEXT_ERASE, model=model, locus="Art. 17(1)")
    assert res.accepted
    # provenance carries auditable char-offset receipts for every element.
    starts = [r["start"] for r in res.provenance["receipts"]]
    assert all(s >= 0 for s in starts)
    assert res.provenance["locus"] == "Art. 17(1)"
