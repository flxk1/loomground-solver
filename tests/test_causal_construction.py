# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Causal construction (the CAUSAL fact-dimension): a model proposes a causal
model, deterministic gates decide. These tests drive a fixed :class:`StubModel`
and assert the GATES fire — EXTRACT a grounded/coherent/high-confidence model
tagging every edge :data:`Dimension.CAUSAL`; keep a PRESUPPOSED link marked
INCOMPLETE and OUT of the grounded set; REJECT an invented STATED span; ESCALATE
on a materially-presupposed (load-bearing-assumed) model, on a self-contradictory
causal model, and on sub-floor confidence. Escalation is a pass, and for the
causal dimension it is the common honest outcome. Outputs are never asserted by
graph-equality; only the gate that fired is."""
from __future__ import annotations

from loomground_solver.causal_construction import (
    construct_causal, StubModel, CausalResult, PresupposedLink,
)
from loomground_solver.dimensions import Dimension
from loomground_solver.reasoning import Edge


# ── canned causal models (fixed; the StubModel returns these verbatim) ────────

# Every stated span below is a verbatim substring of this text.
TEXT_EMISSIONS = (
    "burning fossil fuels emits carbon dioxide which warms the atmosphere"
)

# Two STATED, grounded links — a clean two-hop causal chain.
GROUNDED_CHAIN = {
    "claims": [
        {"cause": "fossil-fuels", "effect": "carbon-dioxide",
         "mechanism": "emits", "status": "stated", "load_bearing": True,
         "cause_span": "burning fossil fuels", "effect_span": "carbon dioxide",
         "mechanism_span": "emits", "confidence": 0.95},
        {"cause": "carbon-dioxide", "effect": "warming",
         "mechanism": "warms", "status": "stated", "load_bearing": True,
         "cause_span": "carbon dioxide", "effect_span": "warms the atmosphere",
         "mechanism_span": "warms", "confidence": 0.93},
    ],
}

# The same two grounded STATED links, plus a NON-load-bearing PRESUPPOSED link
# (the statute assumes CO2 → sea-level rise but never writes it). No spans: a
# presupposed link is surfaced, not grounded.
GROUNDED_PLUS_PRESUPPOSED = {
    "claims": [
        GROUNDED_CHAIN["claims"][0],
        GROUNDED_CHAIN["claims"][1],
        {"cause": "carbon-dioxide", "effect": "sea-level-rise",
         "mechanism": "thermal-expansion", "status": "presupposed",
         "load_bearing": False, "confidence": 0.6},
    ],
}

# An invented STATED link: its effect span is nowhere in the text.
UNGROUNDED_STATED = {
    "claims": [
        {"cause": "fossil-fuels", "effect": "two-degrees",
         "status": "stated", "load_bearing": True,
         "cause_span": "burning fossil fuels",
         "effect_span": "raises global temperature by two degrees",  # not in text
         "confidence": 0.99},
    ],
}

# A statute that states a duty but PRESUPPOSES the load-bearing mechanism.
TEXT_LIABILITY = "the operator of a waste facility is liable for any contamination"
MATERIALLY_PRESUPPOSED = {
    "claims": [
        # a grounded, stated (peripheral) link
        {"cause": "operator", "effect": "liability", "status": "stated",
         "load_bearing": False, "cause_span": "the operator",
         "effect_span": "liable for any contamination", "confidence": 0.95},
        # the load-bearing causal link the statute only assumes
        {"cause": "waste-storage", "effect": "contamination",
         "mechanism": "leaching", "status": "presupposed",
         "load_bearing": True, "confidence": 0.9},
    ],
}

# A causal model that is ENTIRELY presupposed — nothing grounds it.
ENTIRELY_PRESUPPOSED = {
    "claims": [
        {"cause": "storage", "effect": "contamination", "status": "presupposed",
         "load_bearing": False, "confidence": 0.9},
    ],
}

# A self-contradictory STATED model: the switch is said to cause the light on
# AND the light off. Both links are grounded, so the proposal reaches the audit
# gate — which finds the closed causal model inconsistent.
TEXT_SWITCH = "the switch turns the light on and the switch turns the light off"
INCONSISTENT_HIGH_CONF = {
    "claims": [
        {"cause": "switch", "effect": "light-on", "mechanism": "turns",
         "status": "stated", "load_bearing": True, "cause_span": "the switch",
         "effect_span": "the light on", "mechanism_span": "turns",
         "confidence": 0.99},
        {"cause": "switch", "effect": "-light-on", "mechanism": "turns",
         "status": "stated", "load_bearing": True, "cause_span": "the switch",
         "effect_span": "the light off", "mechanism_span": "turns",
         "confidence": 0.99},
    ],
}

# Grounded + coherent, but the weakest STATED link is far below the floor.
SUB_FLOOR = {
    "claims": [
        {"cause": "fossil-fuels", "effect": "carbon-dioxide",
         "mechanism": "emits", "status": "stated", "load_bearing": True,
         "cause_span": "burning fossil fuels", "effect_span": "carbon dioxide",
         "mechanism_span": "emits", "confidence": 0.40},
    ],
}


# ── the gates ─────────────────────────────────────────────────────────────────

def test_grounded_stated_model_is_extracted_and_causal_tagged():
    res = construct_causal(TEXT_EMISSIONS, model=StubModel(GROUNDED_CHAIN))
    assert isinstance(res, CausalResult)
    assert res.extracted and not res.escalated
    assert res.gate_report["grounding"]["ok"] is True
    # every grounded edge is a reasoning.Edge tagged Dimension.CAUSAL.
    assert len(res.grounded_edges) == 2
    assert all(isinstance(e, Edge) for e in res.grounded_edges)
    assert all(e.dimension is Dimension.CAUSAL for e in res.grounded_edges)
    # the predicate carries the named mechanism.
    assert {e.predicate for e in res.grounded_edges} == {"emits", "warms"}


def test_presupposed_link_is_marked_incomplete_and_not_grounded():
    res = construct_causal(TEXT_EMISSIONS,
                           model=StubModel(GROUNDED_PLUS_PRESUPPOSED))
    assert res.extracted                       # the grounded part still extracts
    # only the two STATED links grounded; the presupposed one is NOT an edge.
    assert len(res.grounded_edges) == 2
    assert all(e.object != "sea-level-rise" for e in res.grounded_edges)
    # the presupposed link is surfaced, marked incomplete, never grounded.
    assert len(res.presupposed) == 1
    p = res.presupposed[0]
    assert isinstance(p, PresupposedLink)
    assert p.incomplete is True
    assert p.cause == "carbon-dioxide" and p.effect == "sea-level-rise"
    assert res.gate_report["presupposition"]["presupposed"] == 1


def test_ungrounded_stated_link_is_rejected_never_an_edge():
    res = construct_causal(TEXT_EMISSIONS, model=StubModel(UNGROUNDED_STATED))
    assert res.rejected and res.grounded_edges == ()     # honesty floor #1
    assert not res.escalated                             # a reject, not a defer
    assert res.gate_report["grounding"]["ok"] is False
    assert any("two degrees" in s
               for s in res.gate_report["grounding"]["invented"])


def test_materially_presupposed_model_escalates():
    # a load-bearing causal link is only assumed by the statute → cannot ground
    # what the statute presupposes → escalate, and return NO grounded edges.
    res = construct_causal(TEXT_LIABILITY,
                           model=StubModel(MATERIALLY_PRESUPPOSED))
    assert res.escalated and res.grounded_edges == ()    # escalation is a pass
    assert res.gate_report["materiality"]["ok"] is False
    assert res.gate_report["materiality"]["load_bearing_presupposed"]
    # the presupposed link is still surfaced honestly on the escalation.
    assert any(p.load_bearing and p.effect == "contamination"
               for p in res.presupposed)


def test_entirely_presupposed_model_escalates_nothing_grounded():
    res = construct_causal(TEXT_LIABILITY, model=StubModel(ENTIRELY_PRESUPPOSED))
    assert res.escalated and res.grounded_edges == ()
    assert res.gate_report["materiality"]["nothing_grounded"] is True


def test_inconsistent_causal_model_escalates_despite_high_confidence():
    # honesty: a 0.99-confidence model that has X cause both Y and not-Y does not
    # buy its way to an extraction — the audit gate (interpret.audit) fires.
    res = construct_causal(TEXT_SWITCH, model=StubModel(INCONSISTENT_HIGH_CONF))
    assert res.escalated and res.grounded_edges == ()
    assert res.gate_report["audit"]["verdict"] == "unsound"
    # confidence never even got to overrule the audit.
    assert "confidence" not in res.gate_report


def test_sub_floor_confidence_escalates():
    res = construct_causal(TEXT_EMISSIONS, model=StubModel(SUB_FLOOR))
    assert res.escalated and res.grounded_edges == ()    # escalation is a pass
    assert res.gate_report["confidence"]["ok"] is False
    assert (res.gate_report["confidence"]["min"]
            < res.gate_report["confidence"]["floor"])


def test_stub_model_is_str_to_str_and_no_presupposed_link_is_ever_grounded():
    # The fill seam is ports.ModelFn (str -> str): the stub returns a string
    # completion, stable across calls, that construct_causal decodes.
    model = StubModel(GROUNDED_PLUS_PRESUPPOSED)
    out1, out2 = model("any prompt"), model("a different prompt")
    assert isinstance(out1, str) and out1 == out2        # deterministic
    # Across every shape, the invariant holds: a presupposed link never appears
    # as a grounded edge, and an ungrounded STATED link never yields an edge.
    cases = [
        (TEXT_EMISSIONS, GROUNDED_PLUS_PRESUPPOSED),
        (TEXT_EMISSIONS, UNGROUNDED_STATED),
        (TEXT_LIABILITY, MATERIALLY_PRESUPPOSED),
        (TEXT_SWITCH, INCONSISTENT_HIGH_CONF),
        (TEXT_EMISSIONS, SUB_FLOOR),
    ]
    for text, proposal in cases:
        res = construct_causal(text, model=StubModel(proposal))
        presupposed_effects = {p.effect for p in res.presupposed}
        grounded_effects = {e.object for e in res.grounded_edges}
        assert presupposed_effects.isdisjoint(grounded_effects)
        assert all(e.dimension is Dimension.CAUSAL for e in res.grounded_edges)
    # and the clean model still extracts both grounded edges.
    ok = construct_causal(TEXT_EMISSIONS, model=StubModel(GROUNDED_CHAIN))
    assert ok.extracted and len(ok.grounded_edges) == 2
