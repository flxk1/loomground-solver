# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Contract case — a music 360 / publishing perpetual-buyout clause is void.

A pre-formulated 360 agreement assigns *all* rights in the artist's works in
perpetuity, without adequate participation. Such a standard term causes an
*unangemessene Benachteiligung* (unreasonable disadvantage) contrary to good
faith under §307 Abs. 1 BGB — a mandatory clause-control rule the drafter cannot
contract out of. The elements fire as closed-world / structural conditions (all
SATISFIED), and the operative deontic consequence — the party is *obligated to be
able to disregard* the void clause (§306: the contract stands without it) — is
resolved by the real deontic solver: the statutory norm (lex superior, rank 5)
defeats the drafter's clause (rank 1) → obligatory → SATISFIED. All SATISFIED →
**DETERMINATE (clause void)**. The terminal is COMPUTED from the stages' real
verdicts, never asserted.

This is the contract bucket's primary **signed-replay (H4)** source: its
:class:`DeonticResolution` exposes an intact derivation trace the grader
re-derives and scores PASS.

Probe (must ESCALATE):

  * ``hidden_exception`` — a buried reversion carve-out the publisher says cures
    the imbalance while the artist's counsel calls it illusory: a genuinely
    contested application of the carve-out → the standard evaluator ESCALATES
    rather than answer.
"""
from __future__ import annotations

from ... import (
    CaseSpec, DeonticResolution, Grounding, IntentionalCondition, Probe,
    StandardApplication, StructuralCondition, Terminal, is_a,
)

# The facts the buried-reversion carve-out is applied against. Every benchmark /
# relied-on span below is a verbatim substring of this text.
_CARVEOUT_FACTS = (
    "The 360 agreement assigns all rights in the artist's works in perpetuity; "
    "the publisher argues a buried reversion clause cures the imbalance, while "
    "the artist's counsel considers the reversion illusory."
)

# Genuinely contested application of the carve-out → escalate (never a confident
# 'the imbalance is cured').
_CONTESTED_CARVEOUT = {
    "benchmark": {"span": "a buried reversion clause cures the imbalance",
                  "literal": "reversion_cures_imbalance", "confidence": 1.0},
    "relied_on": [{"span": "assigns all rights in the artist's works in perpetuity",
                   "literal": "perpetual_total_assignment", "confidence": 1.0}],
    "verdict": {"span": "a buried reversion clause cures the imbalance",
                "literal": "carveout_applies", "confidence": 1.0},
    "met": True,
    "contested": True,   # reasonable people could decide either way → escalate
}


CASE = CaseSpec(
    id="contract.music.para307.perpetual_buyout",
    title="Music 360 perpetual-buyout clause is void under §307 BGB",
    case_kind="contract",
    source_text=(
        "§307 Abs. 1 BGB: Bestimmungen in allgemeinen Geschäftsbedingungen sind "
        "unwirksam, wenn sie den Vertragspartner des Verwenders entgegen den "
        "Geboten von Treu und Glauben unangemessen benachteiligen. §306 Abs. 1/2 "
        "BGB: bei Unwirksamkeit bleibt der Vertrag im Übrigen wirksam; an die "
        "Stelle der unwirksamen Klausel treten die gesetzlichen Vorschriften. "
        "Clause: 'The artist assigns all rights in all present and future works "
        "to the publisher, worldwide and in perpetuity.'"
    ),
    question=("Is the perpetual total-buyout clause in the 360 agreement void "
              "under §307 Abs. 1 BGB?"),
    expected_terminal=Terminal.DETERMINATE,   # unreasonable disadvantage → void
    stages=(
        IntentionalCondition(
            name="is_standard_term",
            grounding=Grounding.span("is_standard_term", "§305 Abs. 1 BGB"),
            warrant="§305(1): a pre-formulated, non-negotiated term is an AGB",
            literal="is_pre_formulated_standard_term",
            present=["is_pre_formulated_standard_term",
                     "assigns_all_rights_in_perpetuity"],
        ),
        IntentionalCondition(
            name="perpetual_total_buyout",
            grounding=Grounding.span("perpetual_total_buyout",
                                     "clause: all rights, in perpetuity"),
            warrant="the clause assigns all present and future rights forever "
                    "with no participation reserved to the artist",
            literal="assigns_all_rights_in_perpetuity",
            present=["is_pre_formulated_standard_term",
                     "assigns_all_rights_in_perpetuity"],
        ),
        StructuralCondition(
            name="unreasonable_disadvantage",
            grounding=Grounding.span("unreasonable_disadvantage", "§307 Abs. 1 BGB"),
            warrant="§307(1): a perpetual total buyout is-a clause causing an "
                    "unangemessene Benachteiligung contrary to good faith",
            subject="perpetual_buyout_clause",
            object="section_307_unreasonable_disadvantage",
            edges=[is_a("perpetual_buyout_clause",
                        "one_sided_rights_grab_clause"),
                   is_a("one_sided_rights_grab_clause",
                        "section_307_unreasonable_disadvantage")],
        ),
        DeonticResolution(
            name="disregard_void_clause",
            grounding=Grounding.span("disregard_void_clause",
                                     "§306 i.V.m. §307 BGB"),
            warrant="§306+§307 (lex superior, rank 5) defeats the drafter's "
                    "clause (rank 1): the void term does not bind",
            dimension="intentional",
            norms=[("disregard_void_clause", "obligatory", "§307/§306 BGB", 0, 5),
                   ("disregard_void_clause", "prohibited",
                    "the AGB clause purports to bind", 0, 1)],
            act="disregard_void_clause", pack="lex",   # statute wins → obligatory
        ),
    ),
    probes=(
        Probe(
            kind="hidden_exception",
            note="a buried reversion carve-out the parties genuinely contest",
            stages=(StandardApplication(
                name="reversion_contested",
                grounding=Grounding.span("reversion_contested", "§307 BGB carve-out"),
                warrant="a genuinely contested carve-out is a human's call",
                standard="the buried reversion clause cures the imbalance",
                facts=_CARVEOUT_FACTS, proposal=_CONTESTED_CARVEOUT),),
        ),
    ),
)
