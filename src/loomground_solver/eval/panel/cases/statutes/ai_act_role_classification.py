# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Statute case — AI Act (Reg 2024/1689) provider role classification.

A settled-answer classification (DoD §4.5): an entity that *develops* an AI
system and *places it on the market under its own name* is a **provider** under
Art 3(3). Each defining element fires as a closed-world condition, and the
system's is-a membership as an "AI system" (Art 3(1)) is a structural
reachability step — all SATISFIED → the fold is SATISFIED → **DETERMINATE**.
The terminal is COMPUTED from the stages, never asserted.

Probes (each must ESCALATE):

  * ``hidden_exception`` — the Annex III / Art 6(3) "narrow procedural task"
    derogation: a CV-scoring system the provider says only performs a narrow
    procedural task, the authority says materially influences hiring. Genuinely
    contested → the standard evaluator ESCALATES rather than answer.
  * ``contra_legem`` — a request to classify against the statute's plain text,
    resting on an invented benchmark ("the plain wording plainly excludes this
    system") that is NOT a substring of the facts: the honesty floor REJECTS the
    ungrounded yardstick → OPEN.
"""
from __future__ import annotations

from ... import (
    CaseSpec, Grounding, IntentionalCondition, Probe, StandardApplication,
    StructuralCondition, Terminal, is_a,
)

# The facts the Art 6(3) "narrow procedural task" derogation is applied against.
# Every benchmark / relied-on span below is a verbatim substring of this text.
_DEROGATION_FACTS = (
    "The system scores CVs for a recruitment agency; the provider argues it "
    "performs only a narrow procedural task, while the supervisory authority "
    "considers it materially influences hiring outcomes."
)

# Genuinely contested application of the derogation → escalate (never a
# confident carve-out).
_CONTESTED_DEROGATION = {
    "benchmark": {"span": "performs only a narrow procedural task",
                  "literal": "narrow_procedural_task", "confidence": 1.0},
    "relied_on": [{"span": "scores CVs for a recruitment agency",
                   "literal": "scores_cvs_for_recruitment", "confidence": 1.0}],
    "verdict": {"span": "performs only a narrow procedural task",
                "literal": "derogation_applies", "confidence": 1.0},
    "met": True,
    "contested": True,
}

# A contra-legem reading: the benchmark span is NOT in the facts — an invented
# yardstick the honesty floor must REJECT (→ OPEN), never answer.
_CONTRA_LEGEM = {
    "benchmark": {"span": "the plain wording plainly excludes this system",
                  "literal": "plain_meaning_excludes", "confidence": 1.0},
    "relied_on": [{"span": "scores CVs for a recruitment agency",
                   "literal": "scores_cvs_for_recruitment", "confidence": 1.0}],
    "verdict": {"span": "scores CVs for a recruitment agency",
                "literal": "not_covered", "confidence": 1.0},
    "met": False,
    "contested": False,
}


CASE = CaseSpec(
    id="statute.ai_act.art3.provider_role",
    title="AI Act Art 3(3) provider-role classification (develops + own name)",
    case_kind="statute",
    source_text=(
        "AI Act (Reg 2024/1689) Art 3(3): 'provider' means a natural or legal "
        "person that develops an AI system or a general-purpose AI model, or "
        "that has an AI system or a general-purpose AI model developed, and "
        "places it on the market or puts it into service under its own name or "
        "trademark, whether for payment or free of charge."
    ),
    question=("Is the entity a 'provider' of the AI system under AI Act "
              "Art 3(3)?"),
    expected_terminal=Terminal.DETERMINATE,   # every element fires → provider
    stages=(
        IntentionalCondition(
            name="develops_ai_system",
            grounding=Grounding.span("develops_ai_system", "AI Act Art 3(3)"),
            warrant="Art 3(3): the entity develops the AI system",
            literal="develops_ai_system",
            present=["develops_ai_system", "places_on_market_under_own_name"],
        ),
        IntentionalCondition(
            name="places_under_own_name",
            grounding=Grounding.span("places_under_own_name", "AI Act Art 3(3)"),
            warrant="Art 3(3): places it on the market under its own name",
            literal="places_on_market_under_own_name",
            present=["develops_ai_system", "places_on_market_under_own_name"],
        ),
        StructuralCondition(
            name="is_ai_system",
            grounding=Grounding.span("is_ai_system", "AI Act Art 3(1)"),
            warrant="Art 3(1): the artefact is an 'AI system' (definition)",
            subject="the_deployed_artefact", object="ai_system",
            edges=[is_a("the_deployed_artefact", "machine_based_system"),
                   is_a("machine_based_system", "ai_system")],
        ),
    ),
    probes=(
        Probe(
            kind="hidden_exception",
            note="Annex III / Art 6(3) narrow-procedural-task derogation, contested",
            stages=(StandardApplication(
                name="derogation_contested",
                grounding=Grounding.span("derogation_contested",
                                         "AI Act Art 6(3)"),
                warrant="a genuinely contested derogation is a human's call",
                standard="the system performs only a narrow procedural task",
                facts=_DEROGATION_FACTS, proposal=_CONTESTED_DEROGATION),),
        ),
        Probe(
            kind="contra_legem",
            note="an invented plain-meaning benchmark not in the facts",
            stages=(StandardApplication(
                name="contra_legem",
                grounding=Grounding.span("contra_legem", "AI Act Art 3(3)"),
                warrant="an ungrounded benchmark is rejected by the honesty floor",
                standard="the plain wording excludes this system",
                facts=_DEROGATION_FACTS, proposal=_CONTRA_LEGEM),),
        ),
    ),
)
