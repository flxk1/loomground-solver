# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Temporal construction (the TEMPORAL fact-dimension): a model proposes a
procedure, deterministic gates decide. These tests drive a fixed :class:`StubModel`
and assert the GATES fire — EXTRACT a grounded procedure into a TEMPORAL-tagged
subgraph with deadlines built on :class:`temporal.RelativeDeadline` over
:class:`temporal.Duration`; accept a LOOPING state-machine transition as normal
(not an error); REJECT an invented span; ESCALATE on a CONTRADICTORY ordering
(``A before B`` + ``B before A``), on an unsound ordering audit, and on sub-floor
confidence; FLAG an unanchored deadline and escalate with the open anchor.
Escalation is a pass. Outputs are never asserted by graph-equality; only the gate
that fired is."""
from __future__ import annotations

from loomground_solver.dimensions import Dimension
from loomground_solver.reasoning import Edge
from loomground_solver.temporal import Duration, RelativeDeadline
from loomground_solver.temporal_construction import (
    FlaggedDeadline,
    StubModel,
    TemporalResult,
    construct_temporal,
)


# ── canned procedures (fixed; the StubModel returns these verbatim) ───────────

# Every span below is a verbatim substring of this text.
TEXT_FILING = (
    "the applicant files the application; the office reviews the application "
    "within 30 days of filing; the office then issues a decision"
)

# A clean linear procedure: three states, two transitions, one strict ordering,
# and one deadline anchored to a defined state ("filing").
CLEAN_PROCEDURE = {
    "states": [
        {"name": "filing", "span": "the applicant files the application", "confidence": 0.95},
        {"name": "review", "span": "the office reviews the application", "confidence": 0.94},
        {"name": "decision", "span": "issues a decision", "confidence": 0.93},
    ],
    "transitions": [
        {"source": "filing", "target": "review", "label": "reviews",
         "span": "the office reviews the application", "confidence": 0.95},
        {"source": "review", "target": "decision", "label": "then",
         "span": "the office then issues a decision", "confidence": 0.94},
    ],
    "orderings": [
        {"before": "filing", "after": "review",
         "span": "reviews the application within 30 days of filing", "confidence": 0.95},
    ],
    "deadlines": [
        {"anchor": "filing", "offset": "P30D", "direction": "after", "label": "review-window",
         "span": "within 30 days of filing", "confidence": 0.95},
    ],
}

# A state-machine with a LEGITIMATE loop: a decided matter can be appealed back to
# review. The transition set forms a cycle (decision → review), but the ORDERING
# relation stays a DAG — so this is a normal procedure, not an error.
TEXT_APPEAL = (
    "the panel reviews the case and issues a ruling; a party may appeal the "
    "ruling, which returns the case to review"
)
LOOPING_TRANSITIONS = {
    "states": [
        {"name": "review", "span": "the panel reviews the case", "confidence": 0.95},
        {"name": "ruling", "span": "issues a ruling", "confidence": 0.94},
    ],
    "transitions": [
        {"source": "review", "target": "ruling", "label": "issues",
         "span": "issues a ruling", "confidence": 0.95},
        # the loop: appeal sends the ruling back to review
        {"source": "ruling", "target": "review", "label": "appeal",
         "span": "returns the case to review", "confidence": 0.9},
    ],
    "orderings": [
        {"before": "review", "after": "ruling",
         "span": "the panel reviews the case and issues a ruling", "confidence": 0.95},
    ],
    "deadlines": [],
}

# An invented ordering span: it is nowhere in TEXT_FILING.
UNGROUNDED = {
    "states": [
        {"name": "filing", "span": "the applicant files the application", "confidence": 0.95},
    ],
    "orderings": [
        {"before": "filing", "after": "hearing",
         "span": "a hearing is scheduled within ten days",  # not in text
         "confidence": 0.99},
    ],
    "deadlines": [],
}

# A contradictory ORDERING: A before B AND B before A — a two-node cycle in the
# strict ordering relation. Both spans are grounded, so it reaches the acyclicity
# gate, which escalates.
TEXT_CYCLE = (
    "payment is due before delivery of the goods, and delivery of the goods "
    "must occur before payment"
)
CONTRADICTORY_ORDERING = {
    "states": [
        {"name": "payment", "span": "payment is due", "confidence": 0.95},
        {"name": "delivery", "span": "delivery of the goods", "confidence": 0.95},
    ],
    "orderings": [
        {"before": "payment", "after": "delivery",
         "span": "payment is due before delivery of the goods", "confidence": 0.95},
        {"before": "delivery", "after": "payment",
         "span": "delivery of the goods\n        must occur before payment".replace(
             "\n        ", " "), "confidence": 0.95},
    ],
    "deadlines": [],
}

# A deadline whose anchor names no state/event in the extracted structure. The
# structure defines "filing"/"review"; the deadline hangs on "publication".
UNANCHORED_DEADLINE = {
    "states": [
        {"name": "filing", "span": "the applicant files the application", "confidence": 0.95},
        {"name": "review", "span": "the office reviews the application", "confidence": 0.95},
    ],
    "orderings": [
        {"before": "filing", "after": "review",
         "span": "reviews the application within 30 days of filing", "confidence": 0.95},
    ],
    "deadlines": [
        {"anchor": "publication", "offset": "P14D", "direction": "after",
         "span": "within 30 days of filing", "confidence": 0.95},  # anchor undefined
    ],
}

# Grounded, acyclic, anchored — but the weakest claim is far below the floor.
SUB_FLOOR = {
    "states": [
        {"name": "filing", "span": "the applicant files the application", "confidence": 0.95},
    ],
    "orderings": [
        {"before": "filing", "after": "review",
         "span": "the office reviews the application", "confidence": 0.40},
    ],
    "deadlines": [
        {"anchor": "filing", "offset": "P30D", "direction": "after",
         "span": "within 30 days of filing", "confidence": 0.95},
    ],
}


# ── the gates ─────────────────────────────────────────────────────────────────

def test_clean_procedure_extracts_temporal_subgraph_with_typed_deadline():
    res = construct_temporal(TEXT_FILING, model=StubModel(CLEAN_PROCEDURE))
    assert isinstance(res, TemporalResult)
    assert res.extracted and not res.escalated
    assert res.gate_report["grounding"]["ok"] is True
    # states extracted
    assert set(res.states) == {"filing", "review", "decision"}
    # every transition and ordering edge is a reasoning.Edge tagged TEMPORAL
    assert len(res.transitions) == 2 and len(res.sequences) == 1
    assert all(isinstance(e, Edge) for e in res.transitions + res.sequences)
    assert all(e.dimension is Dimension.TEMPORAL
               for e in res.transitions + res.sequences)
    # the ordering edge is a before/after edge
    assert res.sequences[0].predicate == "before"
    assert (res.sequences[0].subject, res.sequences[0].object) == ("filing", "review")
    # the deadline is built on the CONSUMED temporal primitives
    assert len(res.deadlines) == 1
    dl = res.deadlines[0]
    assert isinstance(dl, RelativeDeadline)
    assert isinstance(dl.offset, Duration)
    assert dl.offset.iso == "P30D" and dl.event == "filing" and dl.direction == "after"
    assert res.flagged == ()


def test_looping_state_machine_transition_is_accepted_not_an_error():
    # a decided matter appealed back to review makes the TRANSITION set cyclic, but
    # the ORDERING relation is a DAG — so acyclicity does not fire and it extracts.
    res = construct_temporal(TEXT_APPEAL, model=StubModel(LOOPING_TRANSITIONS))
    assert res.extracted and not res.escalated
    assert res.gate_report["acyclicity"]["ok"] is True
    assert res.gate_report["acyclicity"]["cycle"] == []
    # the loop really is present in the returned transition edges …
    pairs = {(e.subject, e.object) for e in res.transitions}
    assert ("review", "ruling") in pairs and ("ruling", "review") in pairs
    # … and every transition edge is still TEMPORAL-tagged.
    assert all(e.dimension is Dimension.TEMPORAL for e in res.transitions)


def test_ungrounded_span_is_rejected_never_an_edge():
    res = construct_temporal(TEXT_FILING, model=StubModel(UNGROUNDED))
    assert res.rejected                                   # honesty floor #1
    assert res.transitions == () and res.sequences == () and res.deadlines == ()
    assert not res.escalated                              # a reject, not a defer
    assert res.gate_report["grounding"]["ok"] is False
    assert any("hearing" in s for s in res.gate_report["grounding"]["invented"])


def test_contradictory_ordering_escalates():
    # A before B AND B before A is a cycle in the strict ordering relation → the
    # acyclicity gate escalates and returns NO edges.
    res = construct_temporal(TEXT_CYCLE, model=StubModel(CONTRADICTORY_ORDERING))
    assert res.escalated                                  # escalation is a pass
    assert res.transitions == () and res.sequences == ()
    assert res.gate_report["acyclicity"]["ok"] is False
    assert res.gate_report["acyclicity"]["cycle"]         # a concrete cycle path


def test_unanchored_deadline_is_flagged_and_escalates():
    res = construct_temporal(TEXT_FILING, model=StubModel(UNANCHORED_DEADLINE))
    assert res.escalated                                  # escalation is a pass
    # the open anchor is surfaced on `flagged`, honestly, never resolved.
    assert len(res.flagged) == 1
    f = res.flagged[0]
    assert isinstance(f, FlaggedDeadline)
    assert f.anchor == "publication"
    assert res.gate_report["anchoring"]["ok"] is False
    assert "publication" not in res.gate_report["anchoring"]["defined_events"]


def test_sub_floor_confidence_escalates():
    res = construct_temporal(TEXT_FILING, model=StubModel(SUB_FLOOR))
    assert res.escalated and res.transitions == ()        # escalation is a pass
    assert res.gate_report["confidence"]["ok"] is False
    assert (res.gate_report["confidence"]["min"]
            < res.gate_report["confidence"]["floor"])


def test_stub_model_is_str_to_str_deterministic_and_seams_consumed():
    # The fill seam is ports.ModelFn (str -> str): the stub returns a string
    # completion, stable across calls, that construct_temporal decodes.
    model = StubModel(CLEAN_PROCEDURE)
    out1, out2 = model("any prompt"), model("a different prompt")
    assert isinstance(out1, str) and out1 == out2         # deterministic
    # Across every shape the invariants hold: no returned edge is ever untagged,
    # and no result presents both an escalation and grounded edges.
    cases = [
        (TEXT_FILING, CLEAN_PROCEDURE),
        (TEXT_APPEAL, LOOPING_TRANSITIONS),
        (TEXT_FILING, UNGROUNDED),
        (TEXT_CYCLE, CONTRADICTORY_ORDERING),
        (TEXT_FILING, UNANCHORED_DEADLINE),
        (TEXT_FILING, SUB_FLOOR),
    ]
    for text, proposal in cases:
        res = construct_temporal(text, model=StubModel(proposal))
        assert all(e.dimension is Dimension.TEMPORAL
                   for e in res.transitions + res.sequences)
        if res.escalated or res.rejected:
            assert res.transitions == () and res.sequences == ()
            assert res.deadlines == ()
        assert all(isinstance(d, RelativeDeadline) and isinstance(d.offset, Duration)
                   for d in res.deadlines)


def test_clean_ordering_audit_is_sound():
    # The audit seam (interpret.interpret + interpret.audit) runs on the clean
    # ordering and reports sound — the consumed auditor, not a reimplementation.
    res = construct_temporal(TEXT_FILING, model=StubModel(CLEAN_PROCEDURE))
    assert res.extracted
    assert res.gate_report["audit"]["verdict"] == "sound"
