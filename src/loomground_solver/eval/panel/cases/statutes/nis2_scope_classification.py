# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Statute case — NIS2 (Dir 2022/2555) essential-entity scope (genuinely open).

Not every statutory question is settled. Here the sector is in Annex I
(SATISFIED), but the essential-vs-important classification turns on (a) whether
the entity exceeds the medium-enterprise size-cap (Art 2(1)) — actively
CONTESTED between the parties — and (b) the main-establishment / jurisdiction
fact (Art 26), which is only PRESUPPOSED, never established. Either OPEN
dominates the SATISFIED sector element → the fold is OPEN → **ESCALATE**.

This is the judgment-floor exhibit: the determination is **high-stakes**
(``stake=True``) and open, so R4 requires oversight >= APPROVE and human
origination. Modelled honestly as ESCALATE at ``oversight_level="approve"`` — an
auto-emitted DETERMINATE here would breach the floor and FAIL the grade.

Probe (must ESCALATE):

  * ``unsettled_reading`` — the size-cap reading is a plausible-but-contested
    interpretation; a CONTESTED premise is a human's call → OPEN.
"""
from __future__ import annotations

from ... import (
    CaseSpec, EpistemicPremise, EpistemicStatus, Grounding, IntentionalCondition,
    Probe, Terminal,
)


CASE = CaseSpec(
    id="statute.nis2.art3.essential_entity_scope",
    title="NIS2 essential-entity scope (size-cap contested, jurisdiction presupposed)",
    case_kind="statute",
    source_text=(
        "NIS2 (Dir 2022/2555) Art 3 + Annex I classify entities as 'essential' "
        "or 'important' by sector and size. Art 2(1) applies the Directive to "
        "entities that qualify as medium-sized or exceed the ceilings for "
        "medium-sized enterprises (Recommendation 2003/361/EC). Art 26 fixes "
        "jurisdiction by the entity's main establishment in the Union."
    ),
    question=("Is the entity an 'essential entity' within the scope of NIS2 "
              "Art 3?"),
    expected_terminal=Terminal.ESCALATE,   # OPEN dominates → hand to a human
    stake=True,               # a designation with regulatory/penalty consequences
    oversight_level="approve",  # R4: Esc ∧ Stake ⟹ level >= APPROVE
    stages=(
        IntentionalCondition(
            name="sector_in_annex_i",
            grounding=Grounding.span("sector_in_annex_i", "NIS2 Annex I"),
            warrant="Annex I: the entity operates in a covered sector",
            literal="operates_in_annex_i_sector",
            present=["operates_in_annex_i_sector"],
        ),
        EpistemicPremise(
            name="exceeds_size_cap",
            grounding=Grounding.gap(
                "exceeds_size_cap",
                "whether the entity exceeds the medium-enterprise size-cap "
                "(Art 2(1)) is actively disputed between the parties"),
            warrant="the essential/important split rests on the size classification",
            status=EpistemicStatus.CONTESTED,   # → OPEN
        ),
        EpistemicPremise(
            name="main_establishment",
            grounding=Grounding.gap(
                "main_establishment",
                "the main-establishment fact fixing jurisdiction (Art 26) is "
                "presupposed by the designation but never established"),
            warrant="jurisdiction under Art 26 is a threshold for the designation",
            status=EpistemicStatus.PRESUPPOSED,   # → OPEN
        ),
    ),
    probes=(
        Probe(
            kind="unsettled_reading",
            note="the medium-enterprise size-cap reading is genuinely contested",
            stages=(EpistemicPremise(
                name="size_cap_contested",
                grounding=Grounding.gap("size_cap_contested",
                                        "size-cap reading disputed, not settled"),
                warrant="a contested interpretation is a human's call",
                status=EpistemicStatus.CONTESTED),),
        ),
    ),
)
