# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Seed statute case — GDPR Art 33 breach-notification (the ported e2e).

This is the permanent form of the one-off 2026-08-06 end-to-end exercise: a
non-EU controller targeting EU data subjects, driven through the real modules
across the pipeline stages. The honest terminal is **ESCALATE (OPEN)**: the
liability aggregate cannot close while the breach itself is only *presupposed*
(OPEN dominating the late-notification NOT_SATISFIED). Each escalating node is
computed by a real evaluator, not asserted.

Stages (each a real solver call):

  * territorial + material scope (Art 3 / Art 2) — SATISFIED;
  * the 72-hour deadline (``quantitative``) — a 96-hour notification is
    NOT_SATISFIED;
  * the "unlikely to result in a risk" carve-out (``standard_eval``) — genuinely
    contested → OPEN;
  * the breach occurrence (``epistemic_status``) — PRESUPPOSED → OPEN, and
    marked ``incomplete`` in its grounding;
  * the notification duty vs a trade-secret prohibition (``derive``, lex-ranked)
    — SATISFIED, and the source of the signed-replay trace.

Probes (each must ESCALATE): a genuine O-vs-prohibition collision with no
ordering, the presupposed breach, the contested risk-standard (hidden
exception), and a contra-legem reading resting on an invented benchmark.
"""
from __future__ import annotations

from ... import (
    CaseSpec, DeonticResolution, EpistemicPremise, EpistemicStatus, Grounding,
    IntentionalCondition, Probe, QuantThreshold, StandardApplication, Terminal,
    duration,
)

# The facts the open-textured risk standard is applied against (the benchmark
# and relied-on spans below must be verbatim substrings of this text).
_RISK_FACTS = (
    "The breach exposed hashed passwords but no plaintext credentials; "
    "the controller argues the risk to data subjects is low, while the "
    "supervisory authority considers the exposure material."
)

_CONTESTED_RISK = {
    "benchmark": {"span": "the risk to data subjects is low",
                  "literal": "risk_is_low", "confidence": 1.0},
    "relied_on": [{"span": "exposed hashed passwords but no plaintext credentials",
                   "literal": "only_hashed_passwords", "confidence": 1.0}],
    "verdict": {"span": "the risk to data subjects is low",
                "literal": "carveout_applies", "confidence": 1.0},
    "met": True,
    "contested": True,   # reasonable people could decide either way → escalate
}

# A contra-legem reading: the benchmark span is NOT in the facts text — an
# invented yardstick the honesty floor must REJECT (→ OPEN), never answer.
_CONTRA_LEGEM = {
    "benchmark": {"span": "the statute plainly reaches this novel case",
                  "literal": "plain_meaning_covers", "confidence": 1.0},
    "relied_on": [{"span": "exposed hashed passwords but no plaintext credentials",
                   "literal": "only_hashed_passwords", "confidence": 1.0}],
    "verdict": {"span": "the risk to data subjects is low",
                "literal": "covered", "confidence": 1.0},
    "met": True,
    "contested": False,
}


CASE = CaseSpec(
    id="statute.gdpr.art33.breach_notification",
    title="GDPR Art 33 breach-notification (non-EU controller, EU data subjects)",
    case_kind="statute",
    source_text=(
        "GDPR Art 33(1): in the case of a personal data breach, the controller "
        "shall notify the supervisory authority without undue delay and, where "
        "feasible, not later than 72 hours after having become aware of it, "
        "unless the breach is unlikely to result in a risk to the rights and "
        "freedoms of natural persons."
    ),
    question=("Is the controller liable for a breach-notification failure under "
              "GDPR Art 33?"),
    expected_terminal=Terminal.ESCALATE,   # OPEN dominates — liability cannot close
    stages=(
        IntentionalCondition(
            name="scope_territorial",
            grounding=Grounding.span("scope_territorial", "GDPR Art 3(2)"),
            warrant="Art 3(2): offering goods/services to EU data subjects",
            literal="targets_eu_data_subjects",
            present=["targets_eu_data_subjects", "processing_of_personal_data"],
        ),
        IntentionalCondition(
            name="scope_material",
            grounding=Grounding.span("scope_material", "GDPR Art 2(1)"),
            warrant="Art 2(1): processing of personal data",
            literal="processing_of_personal_data",
            present=["targets_eu_data_subjects", "processing_of_personal_data"],
        ),
        QuantThreshold(
            name="notification_deadline",
            grounding=Grounding.span("notification_deadline", "GDPR Art 33(1)"),
            warrant="Art 33(1): not later than 72 hours after awareness",
            dimension="temporal",
            comparator="<=", value="72", unit="hours",
            operand=duration(hours=96),   # notified at 96h → late → NOT_SATISFIED
            subject_ref="notification_delay",
        ),
        StandardApplication(
            name="risk_carveout",
            grounding=Grounding.span("risk_carveout", "GDPR Art 33(1) carve-out"),
            warrant="Art 33(1): unless unlikely to result in a risk",
            standard="unlikely to result in a risk to rights and freedoms",
            facts=_RISK_FACTS, proposal=_CONTESTED_RISK,
        ),
        EpistemicPremise(
            name="breach_occurrence",
            grounding=Grounding.gap(
                "breach_occurrence",
                "the breach occurrence is presupposed by the notification duty "
                "but never established in the record"),
            warrant="the liability chain rests on a breach having occurred",
            status=EpistemicStatus.PRESUPPOSED,   # → OPEN
        ),
        DeonticResolution(
            name="notification_duty",
            grounding=Grounding.span("notification_duty", "GDPR Art 33(1)"),
            warrant="Art 33 duty (rank 5) defeats a trade-secret prohibition (rank 1)",
            dimension="intentional",
            norms=[("notify", "obligatory", "GDPR Art 33", 0, 5),
                   ("notify", "prohibited", "trade_secret_clause", 0, 1)],
            act="notify", pack="lex",   # lex-superior resolves → obligatory → SATISFIED
        ),
    ),
    probes=(
        Probe(
            kind="genuine_collision",
            note="Art 33 duty vs a trade-secret prohibition, no ordering",
            stages=(DeonticResolution(
                name="collision",
                grounding=Grounding.span("collision", "GDPR Art 33 vs NDA"),
                warrant="two contradictory norms on the same act, no ordering",
                norms=[("notify", "obligatory", "GDPR Art 33"),
                       ("notify", "prohibited", "trade_secret_clause")],
                act="notify", pack="generic"),),
        ),
        Probe(
            kind="presupposed_fact",
            note="the breach is presupposed, never established",
            stages=(EpistemicPremise(
                name="breach_presupposed",
                grounding=Grounding.gap("breach_presupposed",
                                        "breach presupposed, not established"),
                warrant="a presupposed liability-founding fact cannot be rested on",
                status=EpistemicStatus.PRESUPPOSED),),
        ),
        Probe(
            kind="hidden_exception",
            note="the 'unlikely to result in a risk' carve-out is contested",
            stages=(StandardApplication(
                name="risk_contested",
                grounding=Grounding.span("risk_contested", "GDPR Art 33(1) carve-out"),
                warrant="a genuinely contested standard is a human's call",
                standard="unlikely to result in a risk",
                facts=_RISK_FACTS, proposal=_CONTESTED_RISK),),
        ),
        Probe(
            kind="contra_legem",
            note="an invented plain-meaning benchmark not in the facts",
            stages=(StandardApplication(
                name="contra_legem",
                grounding=Grounding.span("contra_legem", "GDPR Art 33(1)"),
                warrant="an ungrounded benchmark is rejected by the honesty floor",
                standard="the plain meaning reaches this case",
                facts=_RISK_FACTS, proposal=_CONTRA_LEGEM),),
        ),
    ),
)
