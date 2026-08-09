# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Gap fork: a model classifies a gap and proposes a Rechtsfortbildung move,
deterministic gates decide. These tests drive a fixed :class:`StubModel` and
assert the GATES + BRANCHES fire:

  * a **planned** gap → ``e_contrario`` with outcome NOT_MET (a determinate
    negative — a pass);
  * a **planwidrig** gap + a grounded like-case → ``analogy``, carried through
    :func:`methods.inference.analogical_inference` (the transfer is observed);
  * an **a-fortiori** move on a planwidrig gap resolves to MET;
  * a **contra-legem** extension over a closed wording → ESCALATE
    (Wortlautgrenze — legislature's job);
  * an **ungrounded** span → REJECT (never returns a move);
  * a **sub-floor** confidence → ESCALATE;
  * an **ambiguous** classification → ESCALATE;
  * a **class/move mismatch** (planned + analogy) → ESCALATE.

Escalation is a pass. Outcomes are never asserted by move-equality alone; the
gate that fired is."""
from __future__ import annotations

from loomground_solver.gap_fork import resolve_gap, StubModel, GapResult


# ── material (every span below is a verbatim substring of text + issue) ────────

TEXT_LIABILITY = "the keeper of a motor vehicle is liable for the damage it causes"
ISSUE_AIRCRAFT = "an aircraft keeper caused damage but no rule addresses aircraft"

# A planwidrig gap closed by analogy: the structure (keeper bears liability) is
# transferred from the like-case (vehicle) to the gap-case (aircraft).
ANALOGY_OK = {
    "gap_class": "planwidrig",
    "move": "analogy",
    "gap": {"span": "no rule addresses aircraft", "literal": "aircraft-keeper",
            "confidence": 0.94},
    "like_case": {"span": "keeper of a motor vehicle", "literal": "vehicle-keeper",
                  "confidence": 0.95},
    "relevant_similarity": {"span": "liable for the damage it causes",
                            "literal": "dangerous-source", "confidence": 0.93},
    "result_literal": "liability",
    "analogy_mapping": {"vehicle_keeper": "aircraft_keeper", "liability": "liability"},
    "analogy_source_relations": [["vehicle_keeper", "bears", "liability"]],
}

# A deliberate legislative silence (beredtes Schweigen) — the inverse conclusion.
TEXT_WRITTEN = "only a written contract is enforceable"
ISSUE_ORAL = "is an oral contract enforceable"
E_CONTRARIO_OK = {
    "gap_class": "planned",
    "move": "e_contrario",
    "gap": {"span": "an oral contract", "literal": "oral-contract",
            "confidence": 0.95},
    "result_literal": "enforceable",
}

# A minore ad maius: a dog is barred, a fortiori a bear (planwidrig, no cap).
TEXT_DOG = "entering the park with a dog is prohibited"
ISSUE_BEAR = "someone wants to enter with a bear"
A_FORTIORI_OK = {
    "gap_class": "planwidrig",
    "move": "a_fortiori_minori_maius",
    "gap": {"span": "enter with a bear", "literal": "bear-entry", "confidence": 0.95},
    "relevant_similarity": {"span": "with a dog is prohibited",
                            "literal": "danger-prohibited", "confidence": 0.94},
    "result_literal": "prohibited",
}

# An extension over a CLOSED enumeration ("only …") — contra legem.
TEXT_MEMBERS = "only registered members may vote at the assembly"
ISSUE_ASSOCIATE = "may an associate member vote"
CONTRA_LEGEM = {
    "gap_class": "planwidrig",
    "move": "analogy",
    "gap": {"span": "an associate member", "literal": "associate", "confidence": 0.95},
    "like_case": {"span": "registered members", "literal": "member",
                  "confidence": 0.95},
    "relevant_similarity": {"span": "may vote", "literal": "voting-interest",
                            "confidence": 0.94},
    "result_literal": "may-vote",
    "analogy_mapping": {"member": "associate", "vote": "vote"},
    "analogy_source_relations": [["member", "may", "vote"]],
}

# An invented like-case span: nowhere in the material.
UNGROUNDED = {
    "gap_class": "planwidrig",
    "move": "analogy",
    "gap": {"span": "no rule addresses aircraft", "literal": "aircraft-keeper",
            "confidence": 0.94},
    "like_case": {"span": "the keeper of a spaceship",   # not in text or issue
                  "literal": "spaceship-keeper", "confidence": 0.95},
    "relevant_similarity": {"span": "liable for the damage it causes",
                            "literal": "dangerous-source", "confidence": 0.93},
    "result_literal": "liability",
    "analogy_mapping": {"vehicle_keeper": "aircraft_keeper"},
    "analogy_source_relations": [["vehicle_keeper", "bears", "liability"]],
}

# Grounded + carried + sound, but the weakest span is far below the floor.
SUB_FLOOR = {
    "gap_class": "planwidrig",
    "move": "analogy",
    "gap": {"span": "no rule addresses aircraft", "literal": "aircraft-keeper",
            "confidence": 0.94},
    "like_case": {"span": "keeper of a motor vehicle", "literal": "vehicle-keeper",
                  "confidence": 0.40},                    # sub-floor
    "relevant_similarity": {"span": "liable for the damage it causes",
                            "literal": "dangerous-source", "confidence": 0.93},
    "result_literal": "liability",
    "analogy_mapping": {"vehicle_keeper": "aircraft_keeper", "liability": "liability"},
    "analogy_source_relations": [["vehicle_keeper", "bears", "liability"]],
}

# A gap the model cannot place as planned XOR planwidrig.
AMBIGUOUS = dict(ANALOGY_OK, gap_class="unclear")

# A deliberate silence the model tries to FILL by analogy — a class/move mismatch.
MISMATCH = dict(ANALOGY_OK, gap_class="planned")


# ── the branches ──────────────────────────────────────────────────────────────

def test_planned_gap_resolves_e_contrario_to_not_met():
    res = resolve_gap(TEXT_WRITTEN, ISSUE_ORAL, model=StubModel(E_CONTRARIO_OK))
    assert isinstance(res, GapResult)
    assert res.status == "not_met" and res.resolved and not res.escalated
    assert res.move == "e_contrario"
    assert res.outcome == "NOT_MET"
    assert res.gate_report["routing"]["ok"] is True


def test_planwidrig_gap_resolves_by_analogy_via_analogical_inference():
    res = resolve_gap(TEXT_LIABILITY, ISSUE_AIRCRAFT, model=StubModel(ANALOGY_OK))
    assert res.status == "resolved" and res.outcome == "MET" and not res.escalated
    assert res.move == "analogy"
    # the analogy primitive genuinely carried the structure across the mapping.
    assert res.gate_report["analogy"]["carried"] is True
    assert res.gate_report["analogy"]["transferred"] == ["aircraft_keeper:bears:liability"]
    assert res.provenance["analogy_transferred"] == ["aircraft_keeper:bears:liability"]
    assert res.like_case == "keeper of a motor vehicle"


def test_a_fortiori_resolves_to_met():
    res = resolve_gap(TEXT_DOG, ISSUE_BEAR, model=StubModel(A_FORTIORI_OK))
    assert res.status == "resolved" and res.outcome == "MET" and not res.escalated
    assert res.move == "a_fortiori_minori_maius"
    assert res.gate_report["audit"]["verdict"] == "sound"


def test_contra_legem_extension_escalates_on_wortlautgrenze():
    res = resolve_gap(TEXT_MEMBERS, ISSUE_ASSOCIATE, model=StubModel(CONTRA_LEGEM))
    assert res.escalated and res.status == "escalated"      # escalation is a pass
    wg = res.gate_report["wortlautgrenze"]
    assert wg["crosses"] is True and wg["wording_cap"].lower() == "only"
    assert "contra legem" in res.reason.lower()


def test_ungrounded_span_is_rejected_never_returns_a_move():
    res = resolve_gap(TEXT_LIABILITY, ISSUE_AIRCRAFT, model=StubModel(UNGROUNDED))
    assert res.rejected and not res.escalated              # a reject, not a defer
    assert res.outcome == ""
    assert res.gate_report["grounding"]["ok"] is False
    assert any("spaceship" in s for s in res.gate_report["grounding"]["invented"])


def test_sub_floor_confidence_escalates():
    res = resolve_gap(TEXT_LIABILITY, ISSUE_AIRCRAFT, model=StubModel(SUB_FLOOR))
    assert res.escalated and res.outcome == ""             # escalation is a pass
    assert res.gate_report["confidence"]["ok"] is False
    assert res.gate_report["confidence"]["min"] < res.gate_report["confidence"]["floor"]


def test_ambiguous_classification_escalates():
    res = resolve_gap(TEXT_LIABILITY, ISSUE_AIRCRAFT, model=StubModel(AMBIGUOUS))
    assert res.escalated
    assert "ambiguous" in res.reason.lower()
    # the classification gate fired before any move execution.
    assert "analogy" not in res.gate_report


def test_planned_plus_analogy_is_a_class_move_mismatch_and_escalates():
    res = resolve_gap(TEXT_LIABILITY, ISSUE_AIRCRAFT, model=StubModel(MISMATCH))
    assert res.escalated and res.status == "escalated"
    assert "beredtes" in res.reason.lower() or "deliberate silence" in res.reason.lower()
    # routing rejected the fill; the analogy transfer was never run.
    assert "analogy" not in res.gate_report


def test_stub_model_is_a_str_to_str_modelfn_and_deterministic():
    model = StubModel(ANALOGY_OK)
    out1, out2 = model("any prompt"), model("a different prompt")
    assert isinstance(out1, str) and out1 == out2
    res = resolve_gap(TEXT_LIABILITY, ISSUE_AIRCRAFT, model=model)
    assert res.resolved
    assert all(r["grounded"] for r in res.provenance["receipts"])
