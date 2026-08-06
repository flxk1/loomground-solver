# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Renewal construction (the contract-lifecycle slice of TEMPORAL): a model
proposes a term + renewal + reversion, deterministic gates decide. These tests
drive a fixed :class:`StubModel` and assert the GATES fire — EXTRACT a clean
auto-renewal (with a grounded notice) as a :class:`temporal.RenewalRule` of kind
``auto`` built on :class:`temporal.Duration`, and a clean option-renewal as kind
``option``, each carried on a :class:`temporal.Term`; REJECT an invented span;
ESCALATE on an AMBIGUOUS kind (never guess auto vs option); FLAG an auto-renewal
with no notice and escalate; FLAG an unanchored reversion and escalate; ESCALATE
on sub-floor confidence. Escalation is a pass. Outputs are never asserted by
object-equality; only the gate that fired, and that the extracted structure is
built on the CONSUMED primitives, is."""
from __future__ import annotations

from loomground_solver.dimensions import Dimension
from loomground_solver.reasoning import Edge
from loomground_solver.temporal import Duration, RenewalRule, Term
from loomground_solver.renewal_construction import (
    NoticeFlag,
    RenewalResult,
    ReversionFlag,
    StubModel,
    construct_renewal,
)


# ── canned contracts (fixed; the StubModel returns these verbatim) ────────────

# Every span below is a verbatim substring of this text.
TEXT_AUTO = (
    "This Agreement has an initial term of one year from the Effective Date. "
    "It renews automatically for successive one-year periods unless either party "
    "gives ninety days' written notice before the end of the then-current term. "
    "All rights granted revert to the Author on termination."
)

# A clean AUTO renewal: a grounded term, an auto kind with a distinguishing span,
# a grounded notice period, and a reversion anchored on a grounded event.
CLEAN_AUTO = {
    "term": {"span": "initial term of one year", "duration": "P1Y", "confidence": 0.95},
    "renewal": {
        "kind": "auto",
        "period": "P1Y",
        "notice": "P90D",
        "span": "renews automatically for successive one-year periods",
        "kind_span": "renews automatically",
        "notice_span": "ninety days' written notice",
        "confidence": 0.94,
    },
    "reversions": [
        {"right": "granted rights", "event": "termination",
         "span": "All rights granted revert to the Author on termination",
         "event_span": "on termination", "confidence": 0.93},
    ],
}

TEXT_OPTION = (
    "The licence runs for a fixed term of two years. The Licensee may renew for "
    "one further two-year period by giving written notice of renewal."
)

# A clean OPTION renewal: renews only on exercise; no notice window is required
# (notice is meaningful for auto, not for an option to renew).
CLEAN_OPTION = {
    "term": {"span": "fixed term of two years", "duration": "P2Y", "confidence": 0.95},
    "renewal": {
        "kind": "option",
        "period": "P2Y",
        "span": "may renew for one further two-year period",
        "kind_span": "may renew",
        "confidence": 0.92,
    },
    "reversions": [],
}

# An invented renewal span: it is nowhere in TEXT_AUTO.
UNGROUNDED = {
    "term": {"span": "initial term of one year", "duration": "P1Y", "confidence": 0.95},
    "renewal": {
        "kind": "auto",
        "period": "P1Y",
        "notice": "P90D",
        "span": "renews perpetually with no right of termination",  # not in text
        "kind_span": "renews automatically",
        "notice_span": "ninety days' written notice",
        "confidence": 0.95,
    },
    "reversions": [],
}

# The text mentions renewal but does not distinguish auto from option: the model
# honestly returns an ambiguous kind. The op must ESCALATE, never guess.
TEXT_AMBIGUOUS = (
    "This Agreement may continue after the initial term of one year for further "
    "periods as the parties see fit."
)
AMBIGUOUS_KIND = {
    "term": {"span": "initial term of one year", "duration": "P1Y", "confidence": 0.95},
    "renewal": {
        "kind": "ambiguous",
        "period": "P1Y",
        "span": "may continue after the initial term of one year for further periods",
        "kind_span": "as the parties see fit",
        "confidence": 0.9,
    },
    "reversions": [],
}

# An AUTO renewal with NO notice period at all — a live auto-renewal trap. The
# kind is grounded and the term is clean, so it clears earlier gates and reaches
# the auto-notice gate, which flags and escalates.
TEXT_AUTO_NO_NOTICE = (
    "This Agreement has an initial term of one year and renews automatically for "
    "successive one-year periods."
)
AUTO_WITHOUT_NOTICE = {
    "term": {"span": "initial term of one year", "duration": "P1Y", "confidence": 0.95},
    "renewal": {
        "kind": "auto",
        "period": "P1Y",
        "span": "renews automatically for successive one-year periods",
        "kind_span": "renews automatically",
        # no notice / notice_span
        "confidence": 0.95,
    },
    "reversions": [],
}

# A clean OPTION renewal but with a reversion whose anchoring event is nowhere in
# the text: unanchored → FLAG and escalate.
TEXT_UNANCHORED = (
    "The licence runs for a fixed term of two years. The Licensee may renew for "
    "one further two-year period by giving written notice of renewal. Rights in "
    "the masters revert to the Artist."
)
UNANCHORED_REVERSION = {
    "term": {"span": "fixed term of two years", "duration": "P2Y", "confidence": 0.95},
    "renewal": {
        "kind": "option",
        "period": "P2Y",
        "span": "may renew for one further two-year period",
        "kind_span": "may renew",
        "confidence": 0.93,
    },
    "reversions": [
        {"right": "rights in the masters", "event": "copyright expiry",
         "span": "Rights in\n the masters revert to the Artist".replace("\n ", " "),
         "event_span": "seventy years after death",  # not in text → unanchored
         "confidence": 0.9},
    ],
}

# Grounded, unambiguous grounded kind, notice present — but the weakest claim is
# far below the floor.
SUB_FLOOR = {
    "term": {"span": "initial term of one year", "duration": "P1Y", "confidence": 0.95},
    "renewal": {
        "kind": "auto",
        "period": "P1Y",
        "notice": "P90D",
        "span": "renews automatically for successive one-year periods",
        "kind_span": "renews automatically",
        "notice_span": "ninety days' written notice",
        "confidence": 0.40,
    },
    "reversions": [],
}


# ── the gates ─────────────────────────────────────────────────────────────────

def test_clean_auto_extracts_renewalrule_kind_auto_on_typed_primitives():
    res = construct_renewal(TEXT_AUTO, model=StubModel(CLEAN_AUTO))
    assert isinstance(res, RenewalResult)
    assert res.extracted and not res.escalated
    assert res.gate_report["grounding"]["ok"] is True
    assert res.gate_report["kind"]["ok"] is True
    # the renewal is the CONSUMED temporal primitive, kind auto, over Durations
    assert isinstance(res.renewal, RenewalRule)
    assert res.renewal.kind == "auto"
    assert isinstance(res.renewal.period, Duration) and res.renewal.period.iso == "P1Y"
    assert isinstance(res.renewal.notice, Duration) and res.renewal.notice.iso == "P90D"
    # the term is a CONSUMED temporal.Term carrying that same renewal rule
    assert isinstance(res.term, Term) and res.term.renewal is res.renewal
    assert res.term.duration is not None and res.term.duration.iso == "P1Y"
    # the notice deadline is computable off the consumed primitives (not re-grown)
    # once the term has a start — the type layer owns that arithmetic, not us.
    # the reversion is a TEMPORAL-tagged reasoning.Edge
    assert len(res.reversions) == 1
    e = res.reversions[0]
    assert isinstance(e, Edge) and e.dimension is Dimension.TEMPORAL
    assert (e.subject, e.object) == ("granted rights", "termination")
    assert res.flagged == ()


def test_clean_option_extracts_renewalrule_kind_option():
    res = construct_renewal(TEXT_OPTION, model=StubModel(CLEAN_OPTION))
    assert res.extracted and not res.escalated
    assert res.gate_report["kind"]["ok"] is True
    assert isinstance(res.renewal, RenewalRule)
    assert res.renewal.kind == "option"
    assert isinstance(res.renewal.period, Duration) and res.renewal.period.iso == "P2Y"
    # an option renewal need not carry a notice window
    assert res.renewal.notice is None
    assert isinstance(res.term, Term) and res.term.renewal is res.renewal
    assert res.reversions == () and res.flagged == ()


def test_ungrounded_span_is_rejected_never_a_renewal():
    res = construct_renewal(TEXT_AUTO, model=StubModel(UNGROUNDED))
    assert res.rejected                                   # honesty floor #1
    assert res.term is None and res.renewal is None and res.reversions == ()
    assert not res.escalated                              # a reject, not a defer
    assert res.gate_report["grounding"]["ok"] is False
    assert any("perpetually" in s for s in res.gate_report["grounding"]["invented"])


def test_ambiguous_kind_escalates_never_guessed():
    # The text does not distinguish auto from option; the op must escalate rather
    # than pick a mechanic. Escalation is a pass.
    res = construct_renewal(TEXT_AMBIGUOUS, model=StubModel(AMBIGUOUS_KIND))
    assert res.escalated                                  # honesty floor #2
    assert res.renewal is None and res.term is None       # nothing guessed
    assert res.gate_report["kind"]["ok"] is False
    assert res.gate_report["kind"]["kind"] not in ("auto", "option")


def test_auto_without_notice_is_flagged_and_escalates():
    res = construct_renewal(TEXT_AUTO_NO_NOTICE, model=StubModel(AUTO_WITHOUT_NOTICE))
    assert res.escalated                                  # honesty floor #3
    assert res.renewal is None                            # not silently accepted
    assert res.gate_report["kind"]["ok"] is True          # kind cleared…
    assert res.gate_report["auto_notice"]["ok"] is False  # …the notice did not
    assert len(res.flagged) == 1
    f = res.flagged[0]
    assert isinstance(f, NoticeFlag) and f.kind == "auto"


def test_unanchored_reversion_is_flagged_and_escalates():
    res = construct_renewal(TEXT_UNANCHORED, model=StubModel(UNANCHORED_REVERSION))
    assert res.escalated                                  # honesty floor #4
    assert res.reversions == ()                           # no edge for a hung reversion
    assert res.gate_report["reversion_anchoring"]["ok"] is False
    assert len(res.flagged) == 1
    f = res.flagged[0]
    assert isinstance(f, ReversionFlag)
    assert f.event == "copyright expiry"


def test_sub_floor_confidence_escalates():
    res = construct_renewal(TEXT_AUTO, model=StubModel(SUB_FLOOR))
    assert res.escalated and res.renewal is None          # escalation is a pass
    assert res.gate_report["confidence"]["ok"] is False
    assert (res.gate_report["confidence"]["min"]
            < res.gate_report["confidence"]["floor"])


def test_stub_model_is_str_to_str_deterministic_and_seams_consumed():
    # The fill seam is ports.ModelFn (str -> str): the stub returns a string
    # completion, stable across calls, that construct_renewal decodes.
    model = StubModel(CLEAN_AUTO)
    out1, out2 = model("any prompt"), model("a different prompt")
    assert isinstance(out1, str) and out1 == out2         # deterministic
    # Across every shape the invariants hold: a renewal, when built, is the
    # consumed temporal.RenewalRule of a valid kind; no result presents both an
    # escalation/rejection and a built renewal or a reversion edge.
    cases = [
        (TEXT_AUTO, CLEAN_AUTO),
        (TEXT_OPTION, CLEAN_OPTION),
        (TEXT_AUTO, UNGROUNDED),
        (TEXT_AMBIGUOUS, AMBIGUOUS_KIND),
        (TEXT_AUTO_NO_NOTICE, AUTO_WITHOUT_NOTICE),
        (TEXT_UNANCHORED, UNANCHORED_REVERSION),
        (TEXT_AUTO, SUB_FLOOR),
    ]
    for text, proposal in cases:
        res = construct_renewal(text, model=StubModel(proposal))
        if res.extracted:
            assert isinstance(res.renewal, RenewalRule)
            assert res.renewal.kind in ("auto", "option")
            assert isinstance(res.renewal.period, Duration)
            assert isinstance(res.term, Term)
            assert all(e.dimension is Dimension.TEMPORAL for e in res.reversions)
        else:
            assert res.renewal is None and res.term is None
            assert res.reversions == ()


def test_clean_lifecycle_audit_is_sound():
    # The audit seam (interpret.interpret + interpret.audit) runs on the clean
    # lifecycle and reports sound — the consumed auditor, not a reimplementation.
    res = construct_renewal(TEXT_AUTO, model=StubModel(CLEAN_AUTO))
    assert res.extracted
    assert res.gate_report["audit"]["verdict"] == "sound"
