# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Relational construction: a model proposes a relation graph of a policy text
(typed roles + relation edges + Hohfeldian jural positions + a relation
composition table), deterministic gates decide. These tests drive a fixed
:class:`StubModel` and assert the GATES fire — EXTRACT a grounded, correlativity-
consistent, composable, high-confidence graph into a subgraph of RELATIONAL-
tagged edges (and a claim-right derives its :func:`deontic.incidents.correlative`
duty); REJECT an invented span; REJECT a relation edge that references an
undeclared role; FLAG a right asserted with no correlative counterparty; ESCALATE
a contested (non-composing) relation chain; ESCALATE on sub-floor confidence —
and that no ungrounded role is ever returned. Escalation is a pass. Outputs are
never asserted by subgraph-equality for the hard cases; only the gate that fired
is."""
from __future__ import annotations

from deontic.incidents import correlative

from loomground_solver.dimensions import Dimension
from loomground_solver.relational_construction import (
    construct_relational, StubModel, RelationalResult,
)


# ── canned relation graphs (fixed; the StubModel returns these verbatim) ───────

# A clean GDPR-flavoured policy. Every span below is a verbatim substring of
# TEXT_CLEAN; the relation chain composes; the claim-right names its counterparty.
TEXT_CLEAN = (
    "the processor acts for the controller; the controller provides service to "
    "the data subject; the data subject has a claim against the controller"
)

GROUNDED_CLEAN = {
    "roles": [
        {"span": "the processor", "name": "processor", "kind": "processor",
         "confidence": 0.97},
        {"span": "the controller", "name": "controller", "kind": "controller",
         "confidence": 0.97},
        {"span": "the data subject", "name": "data-subject", "kind": "subject",
         "confidence": 0.96},
    ],
    "relations": [
        {"span": "the processor acts for the controller", "subject": "processor",
         "predicate": "acts-for", "object": "controller", "confidence": 0.96},
        {"span": "the controller provides service to the data subject",
         "subject": "controller", "predicate": "provides-to",
         "object": "data-subject", "confidence": 0.95},
    ],
    "jural": [
        {"span": "the data subject has a claim against the controller",
         "holder": "data-subject", "incident": "claim",
         "counterparty": "controller", "confidence": 0.95},
    ],
    # acts-for then provides-to composes to a settled relation (provides-to).
    "composition": [
        {"a": "acts-for", "b": "provides-to", "result": "provides-to"},
    ],
    "chains": [["acts-for", "provides-to"]],
}

# An invented role: the span is nowhere in TEXT_CLEAN.
UNGROUNDED = {
    "roles": [
        {"span": "the processor", "name": "processor", "confidence": 0.97},
        {"span": "a supervisory authority",           # not in the text
         "name": "authority", "confidence": 0.99},
    ],
    "relations": [],
    "jural": [],
}

# Grounded spans, but the relation edge points at a role ("regulator") that was
# never declared among the roles — a malformed graph.
TEXT_UNDECLARED = "the processor acts for the controller"
UNDECLARED_ROLE = {
    "roles": [
        {"span": "the processor", "name": "processor", "confidence": 0.97},
        {"span": "the controller", "name": "controller", "confidence": 0.97},
    ],
    "relations": [
        {"span": "the processor acts for the controller", "subject": "processor",
         "predicate": "acts-for", "object": "regulator",   # undeclared
         "confidence": 0.96},
    ],
    "jural": [],
}

# Grounded + well-formed, but a claim-right is asserted with NO counterparty —
# a right that does not tie out to anyone who bears the correlative duty.
TEXT_RIGHT = "the data subject has a claim to erasure"
RIGHT_WITHOUT_CORRELATIVE = {
    "roles": [
        {"span": "the data subject", "name": "data-subject", "confidence": 0.96},
    ],
    "relations": [],
    "jural": [
        {"span": "the data subject has a claim to erasure",
         "holder": "data-subject", "incident": "claim",
         "counterparty": "", "confidence": 0.95},          # no counterparty
    ],
}

# Grounded + well-formed + correlativity-consistent, but the stated relation
# chain is CONTESTED: employs then owns composes to the ESCALATE sentinel.
TEXT_CHAIN = "the employer employs the worker; the worker owns the tool"
NON_COMPOSING_CHAIN = {
    "roles": [
        {"span": "the employer", "name": "employer", "confidence": 0.96},
        {"span": "the worker", "name": "worker", "confidence": 0.96},
        {"span": "the tool", "name": "tool", "confidence": 0.95},
    ],
    "relations": [
        {"span": "the employer employs the worker", "subject": "employer",
         "predicate": "employs", "object": "worker", "confidence": 0.95},
        {"span": "the worker owns the tool", "subject": "worker",
         "predicate": "owns", "object": "tool", "confidence": 0.95},
    ],
    "jural": [],
    "composition": [
        {"a": "employs", "b": "owns", "result": "ESCALATE"},   # contested
    ],
    "chains": [["employs", "owns"]],
}

# Grounded + well-formed + correlativity-consistent + composable, but the
# weakest element sits far below the confidence floor.
SUB_FLOOR = {
    "roles": [
        {"span": "the processor", "name": "processor", "confidence": 0.40},
        {"span": "the controller", "name": "controller", "confidence": 0.95},
    ],
    "relations": [
        {"span": "the processor acts for the controller", "subject": "processor",
         "predicate": "acts-for", "object": "controller", "confidence": 0.95},
    ],
    "jural": [],
}


# ── the gates ─────────────────────────────────────────────────────────────────

def test_clean_graph_is_extracted_with_relational_edges_and_correlative():
    res = construct_relational(TEXT_CLEAN, model=StubModel(GROUNDED_CLEAN))
    assert isinstance(res, RelationalResult)
    assert res.extracted and not res.escalated
    assert res.gate_report["grounding"]["ok"] is True
    assert res.gate_report["correlativity"]["ok"] is True
    assert res.gate_report["composability"]["ok"] is True
    # a real subgraph came back, and every edge is tagged RELATIONAL.
    assert len(res.edges) == 2
    assert all(e.dimension is Dimension.RELATIONAL for e in res.edges)
    assert {e.predicate for e in res.edges} == {"acts-for", "provides-to"}
    # the claim-right derived its deontic.correlative DUTY on the controller.
    assert len(res.correlatives) == 1
    corr = res.correlatives[0]
    assert corr.role == "controller"
    assert corr.incident == correlative("claim") == "duty"
    assert corr.toward == "data-subject"
    # grounded: every receipt is anchored in the text; nothing flagged.
    assert all(r["grounded"] for r in res.provenance["receipts"])
    assert res.flagged == ()


def test_ungrounded_role_is_rejected_never_returns_subgraph():
    res = construct_relational(TEXT_CLEAN, model=StubModel(UNGROUNDED))
    assert res.rejected and res.edges == ()             # honesty floor #1
    assert not res.escalated                            # a reject, not a defer
    assert res.gate_report["grounding"]["ok"] is False
    assert any("supervisory authority" in s
               for s in res.gate_report["grounding"]["invented"])


def test_relation_to_undeclared_role_is_rejected():
    res = construct_relational(TEXT_UNDECLARED, model=StubModel(UNDECLARED_ROLE))
    assert res.rejected and res.edges == ()
    assert res.gate_report["wellformed"]["ok"] is False
    assert any("regulator" in p for p in res.gate_report["wellformed"]["problems"])
    assert "correlativity" not in res.gate_report       # never reached


def test_right_without_correlative_counterparty_is_flagged_and_escalates():
    res = construct_relational(
        TEXT_RIGHT, model=StubModel(RIGHT_WITHOUT_CORRELATIVE))
    assert res.escalated and res.edges == ()            # escalation is a pass
    assert res.gate_report["correlativity"]["ok"] is False
    # the open right is surfaced (holder:incident), not silently dropped.
    assert any("claim" in f for f in res.flagged)
    assert list(res.flagged) == res.gate_report["correlativity"]["flagged"]
    assert "composability" not in res.gate_report       # correlativity fired first


def test_non_composing_chain_escalates_never_fabricates_a_composite():
    res = construct_relational(TEXT_CHAIN, model=StubModel(NON_COMPOSING_CHAIN))
    assert res.escalated and res.edges == ()            # escalation is a pass
    assert res.gate_report["composability"]["ok"] is False
    # the contested chain latched the ESCALATE sentinel in compose_path.
    chains = res.gate_report["composability"]["chains"]
    assert any(c["escalated"] for c in chains)
    assert "confidence" not in res.gate_report          # never reached the floor


def test_sub_floor_confidence_escalates():
    res = construct_relational(TEXT_CLEAN, model=StubModel(SUB_FLOOR))
    assert res.escalated and res.edges == ()            # escalation is a pass
    assert res.gate_report["confidence"]["ok"] is False
    assert (res.gate_report["confidence"]["min"]
            < res.gate_report["confidence"]["floor"])


def test_no_ungrounded_subgraph_ever_returned_and_stub_is_a_str_modelfn():
    # Across every failing shape the invariant holds: no edges are returned
    # unless the construction extracted, and an extracted subgraph is grounded.
    cases = [
        (TEXT_CLEAN, UNGROUNDED),
        (TEXT_UNDECLARED, UNDECLARED_ROLE),
        (TEXT_RIGHT, RIGHT_WITHOUT_CORRELATIVE),
        (TEXT_CHAIN, NON_COMPOSING_CHAIN),
        (TEXT_CLEAN, SUB_FLOOR),
    ]
    for text, proposal in cases:
        res = construct_relational(text, model=StubModel(proposal))
        assert not res.extracted
        assert res.edges == ()

    # The fill seam is ports.ModelFn (str -> str): the stub returns a stable
    # string completion that construct_relational decodes.
    model = StubModel(GROUNDED_CLEAN)
    out1, out2 = model("any prompt"), model("a different prompt")
    assert isinstance(out1, str) and out1 == out2       # deterministic
    ok = construct_relational(TEXT_CLEAN, model=model)
    assert ok.extracted and ok.edges
    assert all(e.dimension is Dimension.RELATIONAL for e in ok.edges)
    assert all(r["grounded"] for r in ok.provenance["receipts"])
    # the audit seam (interpret.audit) ran and found the relation set sound.
    assert ok.gate_report["audit"]["verdict"] == "sound"
    # provenance carries auditable char-offset receipts for every element.
    assert all(r["start"] >= 0 for r in ok.provenance["receipts"])
    assert ok.provenance["text_len"] == len(TEXT_CLEAN)
