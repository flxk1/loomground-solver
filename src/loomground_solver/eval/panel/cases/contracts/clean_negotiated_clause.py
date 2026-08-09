# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Contract case (negative control) — a clean, individually-negotiated clause.

The negative control for the contract bucket: a clause that does NOT collide with
mandatory law. It was *individually negotiated* between commercial parties (so it
is not an AGB at all), and it reserves a fair, reciprocal royalty participation —
it does not unreasonably disadvantage either side. The AGB clause-control
antecedent therefore does not fire: both closed-world elements are NOT_SATISFIED,
and with no OPEN node the fold is NOT_SATISFIED → **NOT_MET**. The 'clause is
void' antecedent is simply not met; nothing is fabricated into voidness. The
terminal is COMPUTED from the stages, never asserted.

No probe: a clean clause carries no fabrication temptation to catch here — the
adversarial probes live on the collision cases. Signed-replay is not applicable
(no deontic stage) → PASS.
"""
from __future__ import annotations

from ... import CaseSpec, Grounding, IntentionalCondition, Terminal


CASE = CaseSpec(
    id="contract.publishing.para307.clean_negotiated_clause",
    title="Individually-negotiated fair-royalty clause — not void (NOT_MET)",
    case_kind="contract",
    source_text=(
        "§305 Abs. 1 Satz 3 BGB: terms individually negotiated between the "
        "parties are not general terms and conditions. §307 Abs. 1 BGB voids an "
        "AGB term that unreasonably disadvantages the counterparty. Clause "
        "(individually negotiated): 'Royalties are shared 50/50 after recoupment, "
        "with the artist retaining an audit right and a 15-year reversion.'"
    ),
    question=("Is the individually-negotiated fair-royalty clause void under "
              "§307 BGB?"),
    expected_terminal=Terminal.NOT_MET,   # antecedent of voidness is not met
    stages=(
        IntentionalCondition(
            name="is_standard_term",
            grounding=Grounding.span("is_standard_term", "§305 Abs. 1 Satz 3 BGB"),
            warrant="§305(1)3: an individually-negotiated term is not an AGB, so "
                    "AGB clause control does not apply",
            literal="is_pre_formulated_standard_term",
            # closed-world: the standard-term literal is ABSENT → NOT_SATISFIED
            present=["is_individually_negotiated_term",
                     "reserves_fair_reciprocal_royalty"],
        ),
        IntentionalCondition(
            name="causes_unreasonable_disadvantage",
            grounding=Grounding.span("causes_unreasonable_disadvantage",
                                     "§307 Abs. 1 BGB"),
            warrant="§307(1): the fair, reciprocal royalty split with audit and "
                    "reversion rights does not unreasonably disadvantage either "
                    "side",
            literal="unreasonably_disadvantages_counterparty",
            # closed-world: the disadvantage literal is ABSENT → NOT_SATISFIED
            present=["is_individually_negotiated_term",
                     "reserves_fair_reciprocal_royalty"],
        ),
    ),
)
