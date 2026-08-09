# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Contract case — an overbroad, perpetual NDA clause: void core, bounded fork.

A pre-formulated NDA binds the counterparty to *perpetual, unlimited*
confidentiality over "all information", with no subject-matter or temporal
ceiling. That the clause is a standard term and reaches without limit fires as
closed-world conditions (SATISFIED). But the *lawful reconstruction* — what
survives once the excess is stripped — is genuinely open: German law forbids a
saving reduction of a void AGB (no geltungserhaltende Reduktion), yet §306 puts
the statutory default in the clause's place, and which lawful ceiling that yields
is contested. That contested reconstruction is an **OPEN** node; the OPEN
dominates the fold. With a bounded, non-empty set of lawful alternatives
declared, the honest terminal is **RESIDUAL** — a void core plus a fork the
human resolves, never a guessed single answer.

The terminal is COMPUTED (OPEN fold + ≥2 residual options → RESIDUAL), never
asserted. No deontic stage here, so signed-replay is not-applicable (PASS).

Probe (must ESCALATE):

  * ``unsettled_reading`` — the plausible-but-contested reading that a perpetual
    ceiling is enforceable "because trade secrets never expire": a genuinely
    contested standard the evaluator ESCALATES rather than resolve.
"""
from __future__ import annotations

from ... import (
    CaseSpec, Grounding, IntentionalCondition, Probe, StandardApplication,
    Terminal,
)

# The facts the lawful-reconstruction standard is applied against. Every
# benchmark / relied-on span below is a verbatim substring of this text.
_SCOPE_FACTS = (
    "The NDA binds the recipient to keep all information confidential forever, "
    "with no defined subject matter and no end date; one reading narrows it to "
    "genuine trade secrets under the GeschGehG, another keeps a fixed-term "
    "ceiling, and the parties dispute which lawful reconstruction governs."
)

# Which lawful reconstruction survives §306 is genuinely contested → OPEN (a
# bounded fork, not a single answer).
_CONTESTED_RECONSTRUCTION = {
    "benchmark": {"span": "one reading narrows it to genuine trade secrets",
                  "literal": "narrow_to_trade_secrets", "confidence": 1.0},
    "relied_on": [{"span": "no defined subject matter and no end date",
                   "literal": "unlimited_scope_and_duration", "confidence": 1.0}],
    "verdict": {"span": "the parties dispute which lawful reconstruction governs",
                "literal": "reconstruction_open", "confidence": 1.0},
    "met": True,
    "contested": True,   # reasonable people could decide either way → escalate
}

# The plausible-but-contested reading probed as an unsettled interpretation.
_UNSETTLED_PERPETUAL = {
    "benchmark": {"span": "keep all information confidential forever",
                  "literal": "perpetual_ceiling_enforceable", "confidence": 1.0},
    "relied_on": [{"span": "genuine trade secrets under the GeschGehG",
                   "literal": "trade_secret_basis", "confidence": 1.0}],
    "verdict": {"span": "keep all information confidential forever",
                "literal": "perpetual_upheld", "confidence": 1.0},
    "met": True,
    "contested": True,
}


CASE = CaseSpec(
    id="contract.nda.para307.perpetual_confidentiality",
    title="Perpetual, unlimited NDA clause — void core, bounded lawful fork",
    case_kind="contract",
    source_text=(
        "§307 Abs. 1/2 BGB: an AGB term that unreasonably disadvantages the "
        "counterparty contrary to good faith is void; a deviation from the "
        "essential idea of the statutory rule indicates such disadvantage. §306: "
        "the statutory provisions take the void clause's place — with NO saving "
        "reduction (geltungserhaltende Reduktion) of the overbroad term. Clause: "
        "'Recipient shall keep all information confidential forever.'"
    ),
    question=("What confidentiality obligation, if any, survives the perpetual "
              "unlimited NDA clause under §§307/306 BGB?"),
    expected_terminal=Terminal.RESIDUAL,   # void core; lawful reconstruction open
    stages=(
        IntentionalCondition(
            name="is_standard_term",
            grounding=Grounding.span("is_standard_term", "§305 Abs. 1 BGB"),
            warrant="§305(1): a pre-formulated, non-negotiated term is an AGB",
            literal="is_pre_formulated_standard_term",
            present=["is_pre_formulated_standard_term",
                     "unlimited_perpetual_confidentiality"],
        ),
        IntentionalCondition(
            name="unlimited_perpetual_scope",
            grounding=Grounding.span("unlimited_perpetual_scope",
                                     "clause: all information, forever"),
            warrant="the clause reaches all information for all time with no "
                    "subject-matter or temporal ceiling",
            literal="unlimited_perpetual_confidentiality",
            present=["is_pre_formulated_standard_term",
                     "unlimited_perpetual_confidentiality"],
        ),
        StandardApplication(
            name="lawful_reconstruction",
            grounding=Grounding.span("lawful_reconstruction", "§306 Abs. 2 BGB"),
            warrant="§306(2): the statutory default replaces the void clause — "
                    "which lawful ceiling that yields is contested",
            standard="the lawful confidentiality that survives §306",
            facts=_SCOPE_FACTS, proposal=_CONTESTED_RECONSTRUCTION,
        ),
    ),
    residual_options=(
        "Sever the clause and apply the GeschGehG trade-secret baseline — "
        "protection limited to genuine trade secrets, for as long as they "
        "remain secret.",
        "Uphold only a fixed-term, subject-matter-bounded confidentiality if a "
        "lawful core is severable from the void excess.",
        "Treat the whole clause as void under §306 with no post-contractual "
        "confidentiality beyond the statutory trade-secret floor.",
    ),
    probes=(
        Probe(
            kind="unsettled_reading",
            note="'trade secrets never expire, so a perpetual ceiling is fine' — "
                 "a plausible but contested reading",
            stages=(StandardApplication(
                name="perpetual_unsettled",
                grounding=Grounding.span("perpetual_unsettled", "§307 BGB"),
                warrant="a genuinely contested reading is a human's call",
                standard="a perpetual confidentiality ceiling is enforceable",
                facts=_SCOPE_FACTS, proposal=_UNSETTLED_PERPETUAL),),
        ),
    ),
)
