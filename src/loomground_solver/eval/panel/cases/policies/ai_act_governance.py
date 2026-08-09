# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Policy case — the EU AI Act (Reg 2024/1689) as a full governance policy.

The whole-instrument governance view (nD meta-norms, roles, risk tiers,
obligations), NOT the narrow Art 3 role/risk statute questions in ``cases/
statutes``. §8.1 STRUCTURED expectation: a 5D+nD subgraph, a definition-closure
map, the six-answer understand-bar, and presupposed-fact probes.

Honesty posture (§8.2): the norm/deontic half is BUILT → the grounded deontic,
structural-taxonomy, temporal-applicability and governance-spine nodes compute
SATISFIED; the factual half — above all the CAUSAL/risk model — is NEEDS-BUILDING
→ those nodes are OPEN (a first-class PASS), never fabricated. The fold is
OPEN-dominant, so the whole-instrument terminal is honestly ESCALATE: the Act
cannot close to DETERMINATE while its risk-tiering rests on a presupposed causal
model and delegated future content.

Every node's verdict is COMPUTED by a real evaluator (structural reachability,
closed-world literal, date order, epistemic settledness, deontic resolution, or
an explicit HonestGap), then graded against the expectation below — never hand-set.
"""
from __future__ import annotations

from ... import (
    CaseSpec, DeonticResolution, EpistemicPremise, EpistemicStatus, Grounding,
    HonestGap, IntentionalCondition, NodeExpectation, PresupposedProbe, Probe,
    StructuralCondition, TemporalOrder, Terminal, UnderstandBar, Verdict, is_a,
)

# Today, as a fixed fact of the case (deterministic — never Date.now()).
_T = "2026-08-06"

_SOURCE = (
    "EU AI Act (Regulation (EU) 2024/1689). Art 1: a high level of protection of "
    "health, safety and fundamental rights and trustworthy, human-centric AI. "
    "Art 3: provider, deployer, importer, distributor, authorised representative. "
    "Art 5: prohibited practices. Art 6 + Annex III: high-risk classification. "
    "Art 9: risk-management system. Art 16: high-risk provider obligations. "
    "Art 25: value-chain obligation allocation. Art 50: transparency / synthetic "
    "content disclosure. Art 51/55: GPAI with systemic risk. Art 53: GPAI provider "
    "obligations. Art 54: non-EU provider authorised representative. Art 40: "
    "harmonised standards presumption of conformity. Art 43: conformity assessment. "
    "Art 56: codes of practice. Art 64-70: AI Office / Board / authorities. "
    "Art 99: penalties up to EUR 35 000 000 or 7% of worldwide turnover. "
    "Art 111/113: entry into force and staggered application."
)


CASE = CaseSpec(
    id="policy.eu.ai_act.governance",
    title="EU AI Act (Reg 2024/1689) as a full governance policy",
    case_kind="policy",
    source_text=_SOURCE,
    question=("Understood as a whole-instrument governance policy: who does the "
              "AI Act govern, under what conditions, with what consequence, "
              "through what procedure, for what purpose, and with what gaps?"),
    expected_terminal=Terminal.ESCALATE,  # OPEN causal/presupposed nodes dominate the fold
    tempting_answer=("the Act fully specifies who is high-risk and exactly what "
                     "they must do, so every obligation resolves determinately"),
    stages=(
        # ── structural — ontology / taxonomy (grounded, reachable is-a) ─────────
        StructuralCondition(
            name="risk-tier-taxonomy",
            grounding=Grounding.span("risk-tier-taxonomy", "Art 5 / Art 6 / Art 50"),
            warrant="the four-tier structure is a textually closed taxonomy",
            subject="prohibited_practice", object="regulated_ai_practice",
            edges=[is_a("prohibited_practice", "regulated_ai_practice")],
        ),
        StructuralCondition(
            name="role-actor-taxonomy",
            grounding=Grounding.span("role-actor-taxonomy", "Art 3(3)-(8)"),
            warrant="provider/deployer/importer/distributor is a closed role set",
            subject="provider", object="operator",
            edges=[is_a("provider", "operator")],
        ),
        StructuralCondition(
            name="annex-iii-enumeration",
            grounding=Grounding.span("annex-iii-enumeration", "Annex III"),
            warrant="the high-risk use-case list is a closed enumerated set",
            subject="biometric_identification", object="annex_iii_high_risk_use",
            edges=[is_a("biometric_identification", "annex_iii_high_risk_use")],
        ),
        # the one honestly-closable defined term — backs definition_closure below
        StructuralCondition(
            name="placing-on-the-market",
            grounding=Grounding.span("placing-on-the-market", "Art 3(9)-(10)"),
            warrant="'first making available on the Union market' reduces to a "
                    "dated first-supply event — a near-primitive",
            subject="placing_on_the_market", object="datable_supply_event",
            edges=[is_a("placing_on_the_market", "datable_supply_event")],
        ),
        StructuralCondition(
            name="high-risk-classification",
            grounding=Grounding.gap(
                "high-risk-classification",
                "whether a GIVEN system is high-risk rests on Annex III mapping "
                "plus the Art 6(3) 'no significant risk' derogation — a "
                "presupposed evaluative judgement; definition-closure NEEDS-BUILDING"),
            warrant="classification of a concrete system is not textually closed",
            subject="candidate_system", object="high_risk",
            edges=[], incomplete_nodes=["candidate_system"],  # unreachable + incomplete → OPEN
        ),
        # ── causal — the THINNEST GAP → all OPEN (never fabricated) ─────────────
        HonestGap(
            name="risk-management-model", dimension="causal",
            grounding=Grounding.gap("risk-management-model",
                                    "Art 9 mandates a risk-management SYSTEM but "
                                    "the underlying system->harm causal model is "
                                    "presupposed; causal construction NEEDS-BUILDING"),
            warrant="a causal harm-model the Act references but never states",
            reason_text="causal-model construction not in panel scope",
        ),
        HonestGap(
            name="harm-causation-to-tier", dimension="causal",
            grounding=Grounding.gap("harm-causation-to-tier",
                                    "risk-tiering rests on a causal link from a "
                                    "system's operation to harm to health/safety/"
                                    "fundamental rights — assumed, not established"),
            warrant="the tiering's causal basis is presupposed",
            reason_text="causal reasoning not in panel scope",
        ),
        EpistemicPremise(
            name="significant-risk-derogation", dimension="causal",
            grounding=Grounding.gap("significant-risk-derogation",
                                    "Art 6(3): an Annex-III system is NOT high-risk "
                                    "if it poses no significant risk — a causal "
                                    "counterfactual presupposed on the facts"),
            warrant="a presupposed causal counterfactual cannot be rested on",
            status=EpistemicStatus.PRESUPPOSED,  # → OPEN
        ),
        HonestGap(
            name="substantial-modification-causation", dimension="causal",
            grounding=Grounding.gap("substantial-modification-causation",
                                    "Art 3(23)/Art 25: whether a change CAUSES a "
                                    "tier/role shift is a causal delta the Act "
                                    "presupposes"),
            warrant="a causal delta judgement the Act does not fix",
            reason_text="causal delta evaluation not in panel scope",
        ),
        # ── temporal — applicability windows (grounded date order) ──────────────
        TemporalOrder(
            name="staggered-applicability",
            grounding=Grounding.span("staggered-applicability", "Art 113"),
            warrant="entry into force precedes today → applicability window open",
            op="on_or_before", left="2024-08-01", right=_T,
        ),
        TemporalOrder(
            name="prohibition-in-force",
            grounding=Grounding.span("prohibition-in-force", "Art 5 / Art 113"),
            warrant="Art 5 prohibitions applicable from 2025-02-02 → in force at T",
            op="on_or_before", left="2025-02-02", right=_T,
        ),
        TemporalOrder(
            name="transparency-obligations-in-force",
            grounding=Grounding.span("transparency-obligations-in-force",
                                     "Art 50 / Art 113"),
            warrant="Art 50 disclosure applicable 2026-08-02 → in force at T",
            op="on_or_before", left="2026-08-02", right=_T,
        ),
        TemporalOrder(
            name="high-risk-transition-window",
            grounding=Grounding.gap("high-risk-transition-window",
                                    "Art 111 grandfathering: whether a given legacy "
                                    "system's transition deadline has run rests on "
                                    "a presupposed placed-on-market date"),
            warrant="the operative date is presupposed, not stated → OPEN",
            op="on_or_before", left=None, right=_T,  # unresolved operand → OPEN
        ),
        # ── relational — roles / value chain ────────────────────────────────────
        IntentionalCondition(
            name="authorised-representative-mandate", dimension="relational",
            grounding=Grounding.span("authorised-representative-mandate", "Art 54"),
            warrant="Art 54: a non-EU provider must appoint an EU representative",
            literal="eu_authorised_representative_duty",
            present=["eu_authorised_representative_duty"],
        ),
        HonestGap(
            name="value-chain-obligation-allocation", dimension="relational",
            grounding=Grounding.gap("value-chain-obligation-allocation",
                                    "Art 25 allocates duties along the chain; WHICH "
                                    "role a given actor occupies rests on presupposed "
                                    "facts about its acts"),
            warrant="actor-role placement is factual and presupposed",
            reason_text="value-chain role attribution not in panel scope",
        ),
        EpistemicPremise(
            name="role-reclassification-on-modification", dimension="relational",
            grounding=Grounding.gap("role-reclassification-on-modification",
                                    "Art 25(1): a deployer becomes a provider on "
                                    "substantial modification — trigger presupposed"),
            warrant="the reclassification trigger rests on presupposed facts",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        HonestGap(
            name="gpai-downstream-integration", dimension="relational",
            grounding=Grounding.gap("gpai-downstream-integration",
                                    "Art 53(2): duties flow from a GPAI-model provider "
                                    "to downstream providers; the integration relation "
                                    "is factual and presupposed"),
            warrant="the downstream integration relation is presupposed",
            reason_text="downstream-integration tracing not in panel scope",
        ),
        # ── intentional — norms + purposes (deontic half, largely grounded) ─────
        IntentionalCondition(
            name="prohibited-practices",
            grounding=Grounding.span("prohibited-practices", "Art 5"),
            warrant="Art 5 enumerates prohibited practices (forbidden)",
            literal="prohibited_practices_enumerated",
            present=["prohibited_practices_enumerated"],
        ),
        IntentionalCondition(
            name="high-risk-provider-obligations",
            grounding=Grounding.span("high-risk-provider-obligations", "Art 16"),
            warrant="Art 16 states the high-risk provider obligation bundle",
            literal="art16_provider_obligation_bundle",
            present=["art16_provider_obligation_bundle"],
        ),
        IntentionalCondition(
            name="gpai-provider-obligations",
            grounding=Grounding.span("gpai-provider-obligations", "Art 53"),
            warrant="Art 53 states GPAI provider duties (docs, copyright, summary)",
            literal="art53_gpai_provider_duties",
            present=["art53_gpai_provider_duties"],
        ),
        IntentionalCondition(
            name="transparency-disclosure-duty",
            grounding=Grounding.span("transparency-disclosure-duty", "Art 50"),
            warrant="Art 50 states synthetic-content / deepfake disclosure duties",
            literal="art50_disclosure_duty",
            present=["art50_disclosure_duty"],
        ),
        EpistemicPremise(
            name="gpai-systemic-risk-duties",
            grounding=Grounding.gap("gpai-systemic-risk-duties",
                                    "Art 51/55: heightened duties attach only to GPAI "
                                    "WITH systemic risk; the designation rests on a "
                                    "presupposed capability/causal judgement"),
            warrant="the systemic-risk designation is a presupposed judgement",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        DeonticResolution(
            name="disclosure-vs-trade-secret-collision",
            grounding=Grounding.gap("disclosure-vs-trade-secret-collision",
                                    "the training-data-summary / documentation duty "
                                    "collides with trade-secret protection, no stated "
                                    "ordering → genuine collision"),
            warrant="two contradictory norms on the same act, no ordering → escalate",
            norms=[("disclose_training_summary", "obligatory", "AI Act Art 53"),
                   ("disclose_training_summary", "prohibited", "trade_secret_clause")],
            act="disclose_training_summary", pack="generic",  # collision → OPEN
        ),
        # ── nD — governance meta-norms ──────────────────────────────────────────
        IntentionalCondition(
            name="enforcement-architecture", dimension="nD",
            grounding=Grounding.span("enforcement-architecture", "Art 64 / 65 / 70"),
            warrant="the meta-norm establishing who governs (AI Office/Board/NCAs)",
            literal="enforcement_bodies_established",
            present=["enforcement_bodies_established"],
        ),
        IntentionalCondition(
            name="conformity-assessment-regime", dimension="nD",
            grounding=Grounding.span("conformity-assessment-regime", "Art 43"),
            warrant="the meta-procedure certifying high-risk compliance",
            literal="conformity_assessment_regime",
            present=["conformity_assessment_regime"],
        ),
        IntentionalCondition(
            name="penalty-schedule", dimension="nD",
            grounding=Grounding.span("penalty-schedule", "Art 99"),
            warrant="Art 99 states a tiered administrative-fine schedule",
            literal="tiered_penalty_schedule",
            present=["tiered_penalty_schedule"],
        ),
        HonestGap(
            name="codes-of-practice-delegated-content", dimension="nD",
            grounding=Grounding.gap("codes-of-practice-delegated-content",
                                    "Art 56 + Art 97 delegated acts: the Act delegates "
                                    "its own future substantive content — meta-norm "
                                    "exists, content under-determined"),
            warrant="delegated substantive content is under-determined",
            reason_text="delegated-content resolution not in panel scope",
        ),
        EpistemicPremise(
            name="standards-presumption-of-conformity", dimension="nD",
            grounding=Grounding.gap("standards-presumption-of-conformity",
                                    "Art 40: the presumption rests on harmonised "
                                    "standards not all yet published"),
            warrant="the presumption rests on standards not yet in existence",
            status=EpistemicStatus.PRESUPPOSED,
        ),
    ),
    expected_subgraph=(
        NodeExpectation("structural", "risk-tier-taxonomy", Verdict.SATISFIED),
        NodeExpectation("structural", "role-actor-taxonomy", Verdict.SATISFIED),
        NodeExpectation("structural", "annex-iii-enumeration", Verdict.SATISFIED),
        NodeExpectation("structural", "placing-on-the-market", Verdict.SATISFIED),
        NodeExpectation("structural", "high-risk-classification", Verdict.OPEN),
        NodeExpectation("causal", "risk-management-model", Verdict.OPEN),
        NodeExpectation("causal", "harm-causation-to-tier", Verdict.OPEN),
        NodeExpectation("causal", "significant-risk-derogation", Verdict.OPEN),
        NodeExpectation("causal", "substantial-modification-causation", Verdict.OPEN),
        NodeExpectation("temporal", "staggered-applicability", Verdict.SATISFIED),
        NodeExpectation("temporal", "prohibition-in-force", Verdict.SATISFIED),
        NodeExpectation("temporal", "transparency-obligations-in-force", Verdict.SATISFIED),
        NodeExpectation("temporal", "high-risk-transition-window", Verdict.OPEN),
        NodeExpectation("relational", "authorised-representative-mandate", Verdict.SATISFIED),
        NodeExpectation("relational", "value-chain-obligation-allocation", Verdict.OPEN),
        NodeExpectation("relational", "role-reclassification-on-modification", Verdict.OPEN),
        NodeExpectation("relational", "gpai-downstream-integration", Verdict.OPEN),
        NodeExpectation("intentional", "prohibited-practices", Verdict.SATISFIED),
        NodeExpectation("intentional", "high-risk-provider-obligations", Verdict.SATISFIED),
        NodeExpectation("intentional", "gpai-provider-obligations", Verdict.SATISFIED),
        NodeExpectation("intentional", "transparency-disclosure-duty", Verdict.SATISFIED),
        NodeExpectation("intentional", "gpai-systemic-risk-duties", Verdict.OPEN),
        NodeExpectation("intentional", "disclosure-vs-trade-secret-collision", Verdict.OPEN),
        NodeExpectation("nD", "enforcement-architecture", Verdict.SATISFIED),
        NodeExpectation("nD", "conformity-assessment-regime", Verdict.SATISFIED),
        NodeExpectation("nD", "penalty-schedule", Verdict.SATISFIED),
        NodeExpectation("nD", "codes-of-practice-delegated-content", Verdict.OPEN),
        NodeExpectation("nD", "standards-presumption-of-conformity", Verdict.OPEN),
    ),
    definition_closure={
        # honest: recursive definition-closure is NEEDS-BUILDING (§8.2). Only
        # placing-on-the-market is backed by a same-named SATISFIED structural
        # stage; every other core term stays OPEN (an honest pass), never faked.
        "placing-on-the-market": "resolves_to_primitives",
        "ai-system": "OPEN",
        "high-risk-ai-system": "OPEN",
        "gpai-model": "OPEN",
        "provider": "OPEN",
        "deployer": "OPEN",
        "substantial-modification": "OPEN",
        "systemic-risk": "OPEN",
    },
    understand_bar=UnderstandBar(
        who_what=("Providers, deployers, importers, distributors and authorised "
                  "representatives of AI systems and GPAI models placed on the "
                  "Union market or put into service (Art 2 scope; Art 3 roles)."),
        conditions=("Obligations are conditioned on risk-tier (Art 5 / Art 6+Annex "
                    "III / Art 50) and role. OPEN: the tier-triggering facts "
                    "(is-this-high-risk, does-a-modification-count, systemic-risk) "
                    "are referenced but not established by the Act."),
        consequence=("Prohibited practices forbidden (Art 5); high-risk providers "
                     "carry the Art 16 bundle + conformity assessment (Art 43); "
                     "GPAI providers carry Art 53 duties; Art 50 transparency; "
                     "breach draws Art 99 tiered fines."),
        procedure=("Conformity assessment + CE marking + EU-database registration; "
                   "post-market monitoring + serious-incident reporting; staggered "
                   "applicability (Art 113). OPEN where the presumption of conformity "
                   "depends on Art 40 harmonised standards not yet published."),
        purpose=("Art 1: a high level of protection of health, safety and fundamental "
                 "rights and trustworthy, human-centric AI, supporting innovation "
                 "and the internal market."),
        gaps=("OPEN: the causal harm-model behind risk-tiering, ex-ante knowability "
              "of a system's tier, recursive definition-closure of the core terms, "
              "and substantive content delegated to future codes/standards/acts."),
    ),
    presupposed_probes=(
        PresupposedProbe("risk-tier-knowable-ex-ante", Terminal.ESCALATE),
        PresupposedProbe("substantial-modification-determinable", Terminal.ESCALATE),
        PresupposedProbe("systemic-risk-capability-measurable", Terminal.ESCALATE),
        PresupposedProbe("harmonised-standards-exist", Terminal.ESCALATE),
    ),
    probes=(
        Probe(
            kind="genuine_collision",
            note="the training-data-summary duty vs a trade-secret prohibition",
            stages=(DeonticResolution(
                name="disclosure_collision",
                grounding=Grounding.span("disclosure_collision", "Art 53 vs NDA"),
                warrant="two contradictory norms on the same act, no ordering",
                norms=[("disclose_training_summary", "obligatory", "AI Act Art 53"),
                       ("disclose_training_summary", "prohibited", "trade_secret_clause")],
                act="disclose_training_summary", pack="generic"),),
        ),
        Probe(
            kind="presupposed_fact",
            note="a provider's risk tier is presupposed knowable ex ante",
            stages=(EpistemicPremise(
                name="risk_tier_presupposed",
                grounding=Grounding.gap("risk_tier_presupposed",
                                        "the risk tier is presupposed, not established"),
                warrant="a presupposed tier-founding fact cannot be rested on",
                status=EpistemicStatus.PRESUPPOSED),),
        ),
        Probe(
            kind="unsettled_reading",
            note="whether the Art 6(3) 'no significant risk' derogation applies",
            stages=(EpistemicPremise(
                name="art63_derogation_unsettled",
                grounding=Grounding.gap("art63_derogation_unsettled",
                                        "the derogation's application is contested"),
                warrant="a contested reading is a human's call, not the engine's",
                status=EpistemicStatus.CONTESTED),),
        ),
    ),
)
