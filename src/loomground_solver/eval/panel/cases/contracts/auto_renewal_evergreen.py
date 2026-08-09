# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Contract case — an evergreen auto-renewal term with an ambiguous mechanic.

A music-services contract renews for a further term, but the drafting is
genuinely ambiguous: it is unclear whether renewal is *automatic unless
cancelled* (an evergreen roll-over, restricted by §309 Nr. 9 BGB) or an *option*
the label must affirmatively exercise. The temporal shape is real — the renewal
date falls after signing, so the ordering condition is SATISFIED — but the
renewal *mechanic* (auto vs option) is contested and cannot be resolved from the
text. That contested premise is an **OPEN** node; OPEN dominates the fold. With
no bounded option-set declared, the honest terminal is **ESCALATE** — the layer
must never guess auto-vs-option. The terminal is COMPUTED, never asserted.

This is a high-stakes, personal-advice-flavoured question ("should I, an
individual artist, sign this?"), so the judgment floor is exercised: ``personal``
raises the required oversight to MANUAL, and the honest OPEN resolution keeps
origination with the human (no auto-emitted answer) → the floor gate PASSES.

Probe (must ESCALATE):

  * ``presupposed_fact`` — whether cancellation notice was in fact given is
    presupposed by any 'it renewed' reading but never established → OPEN.
"""
from __future__ import annotations

from ... import (
    CaseSpec, EpistemicPremise, EpistemicStatus, Grounding, IntentionalCondition,
    Probe, TemporalOrder, Terminal,
)


CASE = CaseSpec(
    id="contract.services.para309n9.auto_renewal_evergreen",
    title="Evergreen auto-renewal term with an ambiguous auto-vs-option mechanic",
    case_kind="contract",
    source_text=(
        "§309 Nr. 9 BGB: in standard terms, a clause tacitly extending a "
        "continuing-obligation contract is void where it binds the customer for "
        "more than one year, extends by more than one year, or sets a notice "
        "period longer than three months before the term's end. Clause: 'This "
        "agreement continues for a further term'; the text does not say whether "
        "continuation is automatic-unless-cancelled or an option the label must "
        "exercise."
    ),
    question=("Did the music-services agreement renew, and on what mechanic, "
              "under the evergreen clause and §309 Nr. 9 BGB?"),
    expected_terminal=Terminal.ESCALATE,   # renewal mechanic genuinely ambiguous
    stake=True,
    personal=True,
    oversight_level="manual",              # personal ⟹ floor = MANUAL
    stages=(
        IntentionalCondition(
            name="is_standard_term",
            grounding=Grounding.span("is_standard_term", "§305 Abs. 1 BGB"),
            warrant="§305(1): a pre-formulated, non-negotiated term is an AGB",
            literal="is_pre_formulated_standard_term",
            present=["is_pre_formulated_standard_term",
                     "continuing_obligation_contract"],
        ),
        TemporalOrder(
            name="renewal_after_signing",
            grounding=Grounding.span("renewal_after_signing",
                                     "contract dates: signed 2026-01-01, "
                                     "renewal 2027-01-01"),
            warrant="the renewal date falls after signing — the temporal shape "
                    "of the roll-over is well-formed",
            op="after", left="2027-01-01", right="2026-01-01",
        ),
        EpistemicPremise(
            name="renewal_mechanic",
            grounding=Grounding.gap(
                "renewal_mechanic",
                "whether continuation is automatic-unless-cancelled or an "
                "option to be exercised is contested and unresolved in the text"),
            warrant="the answer turns on the renewal mechanic, which the "
                    "drafting leaves genuinely ambiguous",
            status=EpistemicStatus.CONTESTED,   # → OPEN
        ),
    ),
    probes=(
        Probe(
            kind="presupposed_fact",
            note="whether cancellation notice was given is presupposed, never "
                 "established",
            stages=(EpistemicPremise(
                name="notice_given_presupposed",
                grounding=Grounding.gap("notice_given_presupposed",
                                        "notice-given is presupposed, not established"),
                warrant="a presupposed fact the outcome turns on cannot be "
                        "rested on",
                status=EpistemicStatus.PRESUPPOSED),),
        ),
    ),
)
