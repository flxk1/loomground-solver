# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Structural construction: a model proposes an ontology of a policy text
(concepts + is-a/part-of edges + definitions), deterministic gates decide. These
tests drive a fixed :class:`StubModel` and assert the GATES fire — EXTRACT a
grounded/acyclic/closed/high-confidence ontology into a subgraph of
STRUCTURAL-tagged edges, REJECT an invented span, ESCALATE a cyclic hierarchy,
FLAG an undefined term, ESCALATE on sub-floor confidence and on an inconsistent
hierarchy — and that no ungrounded concept and no cyclic hierarchy is ever
returned. Escalation is a pass. Outputs are never asserted by subgraph-equality
for the hard cases; only the gate that fired is."""
from __future__ import annotations

from loomground_solver.dimensions import Dimension
from loomground_solver.structural_construction import (
    construct_structure, StubModel, StructuralResult,
)


# ── canned ontologies (fixed; the StubModel returns these verbatim) ────────────

# A clean policy: every span below is a verbatim substring of TEXT_POLICY, the
# hierarchy is a DAG, and every used term resolves to a declared concept or a
# definition.
TEXT_POLICY = (
    "a controller is an organisation; a processor is an organisation; "
    "personal data is information held by the controller"
)

GROUNDED_CLEAN = {
    "concepts": [
        {"span": "a controller", "name": "controller", "confidence": 0.97},
        {"span": "a processor", "name": "processor", "confidence": 0.96},
        {"span": "an organisation", "name": "organisation", "confidence": 0.95},
        {"span": "personal data", "name": "personal-data", "confidence": 0.94},
        {"span": "information", "name": "information", "confidence": 0.95},
    ],
    "edges": [
        {"span": "a controller is an organisation", "subject": "controller",
         "predicate": "is-a", "object": "organisation", "confidence": 0.96},
        {"span": "a processor is an organisation", "subject": "processor",
         "predicate": "is-a", "object": "organisation", "confidence": 0.95},
    ],
    "definitions": [
        {"span": "personal data is information held by the controller",
         "term": "personal-data", "uses": ["information", "controller"],
         "confidence": 0.93},
    ],
}

# An invented concept: the span is nowhere in TEXT_POLICY.
UNGROUNDED = {
    "concepts": [
        {"span": "a controller", "name": "controller", "confidence": 0.97},
        {"span": "a supervisory authority",           # not in the text
         "name": "authority", "confidence": 0.99},
    ],
    "edges": [],
    "definitions": [],
}

# A cyclic is-a hierarchy: module → component → module. Every span is grounded.
TEXT_CYCLE = "a module is a component and a component is a module"
CYCLIC = {
    "concepts": [
        {"span": "a module", "name": "module", "confidence": 0.98},
        {"span": "a component", "name": "component", "confidence": 0.98},
    ],
    "edges": [
        {"span": "a module is a component", "subject": "module",
         "predicate": "is-a", "object": "component", "confidence": 0.97},
        {"span": "a component is a module", "subject": "component",
         "predicate": "is-a", "object": "module", "confidence": 0.97},
    ],
    "definitions": [],
}

# Grounded + acyclic, but a definition draws on a term ("algorithm") that is
# neither a declared concept, defined, nor marked external/primitive.
TEXT_OPEN = "personal data is information processed by an algorithm"
UNDEFINED_TERM = {
    "concepts": [
        {"span": "personal data", "name": "personal-data", "confidence": 0.95},
        {"span": "information", "name": "information", "confidence": 0.95},
    ],
    "edges": [],
    "definitions": [
        {"span": "personal data is information processed by an algorithm",
         "term": "personal-data", "uses": ["information", "algorithm"],
         "confidence": 0.94},
    ],
}

# Grounded + acyclic + closed, but the weakest element is far below the floor.
SUB_FLOOR = {
    "concepts": [
        {"span": "a controller", "name": "controller", "confidence": 0.40},
        {"span": "an organisation", "name": "organisation", "confidence": 0.95},
    ],
    "edges": [
        {"span": "a controller is an organisation", "subject": "controller",
         "predicate": "is-a", "object": "organisation", "confidence": 0.95},
    ],
    "definitions": [],
}

# A self-contradictory concept set ("open" and "-open"), proposed with very high
# confidence. Grounded, acyclic (no edges) and closed, so it reaches the audit
# gate — which finds the closure inconsistent.
TEXT_CONTRA = "the gate is open and the gate is not open"
INCONSISTENT_HIGH_CONF = {
    "concepts": [
        {"span": "the gate is open", "name": "open", "confidence": 0.99},
        {"span": "is not open", "name": "-open", "confidence": 0.99},
    ],
    "edges": [],
    "definitions": [],
}


# ── the gates ─────────────────────────────────────────────────────────────────

def test_grounded_acyclic_closed_is_extracted_with_structural_edges():
    res = construct_structure(TEXT_POLICY, model=StubModel(GROUNDED_CLEAN))
    assert isinstance(res, StructuralResult)
    assert res.extracted and not res.escalated
    assert res.gate_report["grounding"]["ok"] is True
    assert res.gate_report["acyclicity"]["ok"] is True
    assert res.gate_report["closure"]["ok"] is True
    # a real subgraph came back, and every edge is tagged STRUCTURAL.
    assert len(res.edges) == 2
    assert all(e.dimension is Dimension.STRUCTURAL for e in res.edges)
    assert {e.predicate for e in res.edges} == {"is-a"}
    # grounded: every receipt is anchored in the text; nothing flagged.
    assert all(r["grounded"] for r in res.provenance["receipts"])
    assert res.flagged == ()
    assert len(res.concepts) == 5


def test_ungrounded_concept_is_rejected_never_returns_subgraph():
    res = construct_structure(TEXT_POLICY, model=StubModel(UNGROUNDED))
    assert res.rejected and res.edges == ()             # honesty floor #1
    assert not res.escalated                            # a reject, not a defer
    assert res.gate_report["grounding"]["ok"] is False
    assert any("supervisory authority" in s
               for s in res.gate_report["grounding"]["invented"])


def test_cyclic_hierarchy_escalates_never_returned():
    res = construct_structure(TEXT_CYCLE, model=StubModel(CYCLIC))
    assert res.escalated and res.edges == ()            # escalation is a pass
    assert res.gate_report["acyclicity"]["ok"] is False
    # the reported cycle closes back on itself.
    cyc = res.gate_report["acyclicity"]["cycle"]
    assert cyc and cyc[0] == cyc[-1]
    assert "confidence" not in res.gate_report          # never reached the floor


def test_undefined_term_is_flagged_and_escalates():
    res = construct_structure(TEXT_OPEN, model=StubModel(UNDEFINED_TERM))
    assert res.escalated and res.edges == ()
    assert res.gate_report["closure"]["ok"] is False
    assert "algorithm" in res.flagged                   # the open term is surfaced
    assert "algorithm" in res.gate_report["closure"]["undefined"]


def test_sub_floor_confidence_escalates():
    res = construct_structure(TEXT_POLICY, model=StubModel(SUB_FLOOR))
    assert res.escalated and res.edges == ()            # escalation is a pass
    assert res.gate_report["confidence"]["ok"] is False
    assert (res.gate_report["confidence"]["min"]
            < res.gate_report["confidence"]["floor"])


def test_inconsistent_hierarchy_escalates_despite_high_confidence():
    # confidence is never trusted alone: a 0.99-confidence but internally
    # contradictory concept set does not buy its way past the audit gate.
    res = construct_structure(TEXT_CONTRA, model=StubModel(INCONSISTENT_HIGH_CONF))
    assert res.escalated and res.edges == ()
    assert res.gate_report["audit"]["verdict"] == "unsound"
    assert "confidence" not in res.gate_report          # audit fired first


def test_no_ungrounded_or_cyclic_subgraph_is_ever_returned():
    # Across every failing shape the invariant holds: no edges are returned
    # unless the construction extracted, and an extracted subgraph is grounded.
    cases = [
        (TEXT_POLICY, UNGROUNDED),
        (TEXT_CYCLE, CYCLIC),
        (TEXT_OPEN, UNDEFINED_TERM),
        (TEXT_POLICY, SUB_FLOOR),
        (TEXT_CONTRA, INCONSISTENT_HIGH_CONF),
    ]
    for text, proposal in cases:
        res = construct_structure(text, model=StubModel(proposal))
        assert not res.extracted
        assert res.edges == ()
    ok = construct_structure(TEXT_POLICY, model=StubModel(GROUNDED_CLEAN))
    assert ok.extracted and ok.edges
    assert all(e.dimension is Dimension.STRUCTURAL for e in ok.edges)
    assert all(r["grounded"] for r in ok.provenance["receipts"])


def test_stub_model_is_a_str_to_str_modelfn_and_deterministic():
    # The fill seam is ports.ModelFn (str -> str): the stub returns a string
    # completion, stable across calls, that construct_structure decodes.
    model = StubModel(GROUNDED_CLEAN)
    out1 = model("any prompt")
    out2 = model("a different prompt")
    assert isinstance(out1, str) and out1 == out2       # deterministic
    res = construct_structure(TEXT_POLICY, model=model)
    assert res.extracted
    # provenance carries auditable char-offset receipts for every element.
    starts = [r["start"] for r in res.provenance["receipts"]]
    assert all(s >= 0 for s in starts)
    assert res.provenance["text_len"] == len(TEXT_POLICY)
