# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Statute case — DORA (Reg 2022/2554) major-incident notification duty.

The initial-notification duty in Art 19(1) is triggered only by a *major*
ICT-related incident. Here the entity is in scope (Art 2) and an incident is
established (ASSERTED), but the materiality classification (Art 18 / the RTS
threshold, modelled as "service downtime of at least 24 hours") is NOT met — the
outage lasted two hours. Some sub-issue NOT_SATISFIED, ZERO OPEN → the fold is
NOT_SATISFIED → **NOT_MET**: the duty is not triggered. Computed, not asserted.

Probe (must ESCALATE):

  * ``presupposed_fact`` — the very question "was the incident *major*?" If that
    classification is only *presupposed* (never established), it is an unsettled
    liability-founding premise → OPEN. The honest layer never fabricates the
    materiality it was not given.
"""
from __future__ import annotations

from ... import (
    CaseSpec, EpistemicPremise, EpistemicStatus, Grounding, IntentionalCondition,
    Probe, QuantThreshold, Terminal, duration,
)


CASE = CaseSpec(
    id="statute.dora.art19.major_incident_notification",
    title="DORA Art 19 major-incident notification (incident not major → no duty)",
    case_kind="statute",
    source_text=(
        "DORA (Reg 2022/2554) Art 19(1): financial entities shall report major "
        "ICT-related incidents to the relevant competent authority. Art 18 "
        "classifies an incident as 'major' by reference to criteria (clients "
        "affected, data losses, duration and service downtime, economic "
        "impact) specified in the regulatory technical standards."
    ),
    question=("Must the financial entity submit an initial major-incident "
              "notification under DORA Art 19(1)?"),
    expected_terminal=Terminal.NOT_MET,   # incident is not 'major' → duty untriggered
    stages=(
        IntentionalCondition(
            name="scope_financial_entity",
            grounding=Grounding.span("scope_financial_entity", "DORA Art 2(1)"),
            warrant="Art 2(1): a credit institution is a financial entity in scope",
            literal="is_financial_entity_in_scope",
            present=["is_financial_entity_in_scope", "ict_incident_occurred"],
        ),
        EpistemicPremise(
            name="incident_established",
            grounding=Grounding.span("incident_established",
                                     "DORA incident register entry"),
            warrant="the incident is recorded in the register (asserted, sourced)",
            status=EpistemicStatus.ASSERTED,   # settled → SATISFIED
        ),
        QuantThreshold(
            name="major_downtime_threshold",
            grounding=Grounding.span("major_downtime_threshold",
                                     "DORA Art 18 classification RTS"),
            warrant="Art 18/RTS: 'major' requires service downtime of >= 24 hours",
            dimension="temporal",
            comparator=">=", value="24", unit="hours",
            operand=duration(hours=2),   # a 2-hour outage → below the threshold
            subject_ref="service_downtime",
        ),
    ),
    probes=(
        Probe(
            kind="presupposed_fact",
            note="'was the incident major?' presupposed, never classified",
            stages=(EpistemicPremise(
                name="majority_presupposed",
                grounding=Grounding.gap(
                    "majority_presupposed",
                    "the 'major' classification is presupposed by the duty but "
                    "never established against the Art 18 criteria"),
                warrant="a presupposed materiality classification cannot be rested on",
                status=EpistemicStatus.PRESUPPOSED),),
        ),
    ),
)
