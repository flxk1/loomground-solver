# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Policy case — the EU Digital Services Act (Reg (EU) 2022/2065) as a full
platform-obligations policy.

The whole-instrument governance view of the DSA (the intermediary is-a taxonomy,
the tiered actor value-chain, notice-and-action, transparency cadences, VLOP
systemic-risk assessment/mitigation, recommender transparency and redress), NOT
a narrow single-article statute question. §8.1 STRUCTURED expectation: a 5D+nD
subgraph, a definition-closure map, the six-answer understand-bar, and
presupposed-fact probes.

Honesty posture (§8.2): the DSA is well-drafted, so its structural is-a
backbone — including the MULTI-HOP reachability online-platform IS-A hosting
IS-A intermediary, and VLOP IS-A online-platform — the relational actor
value-chain, the temporal reporting cadences and the stated-norm/deontic half
all compute SATISFIED. But the CAUSAL systemic-risk → mitigation model is the
thinnest gap (NEEDS-BUILDING): every causal node is honestly OPEN, never
fabricated, and load-bearing world-facts (the 45M VLOP threshold count, whether
content is "illegal", whether a mitigation is "effective") are presupposed. The
fold is OPEN-dominant, so the whole-instrument terminal is honestly ESCALATE:
the DSA is grounded where it states things, but cannot close to DETERMINATE
while its risk model and its world-facts are presupposed. Grounded != verified.

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
    "EU Digital Services Act (Regulation (EU) 2022/2065). Art 1: a safe, "
    "predictable and trusted online environment; protection of fundamental "
    "rights. Art 3: definitions — intermediary service (mere conduit / caching "
    "/ hosting), online platform, recipient of the service, illegal content, "
    "dissemination to the public, active recipient. Art 6: hosting liability "
    "exemption conditioned on expeditious action. Art 13: legal representative. "
    "Art 15/24/42: transparency reporting. Art 16: notice-and-action. Art 17: "
    "statement of reasons. Art 20/21: internal complaint-handling + out-of-court "
    "dispute settlement. Art 22: trusted flaggers. Art 26/27/38: advertising + "
    "recommender-system transparency. Art 33: VLOP/VLOSE designation (45M "
    "threshold). Art 34/35/36: systemic-risk assessment, mitigation, crisis "
    "response. Art 37: independent audit. Art 49-56: Digital Services "
    "Coordinators + Commission supervision. Art 61-63: European Board. Art 74: "
    "fines up to 6% of worldwide annual turnover. Art 87: delegated/implementing "
    "acts."
)


CASE = CaseSpec(
    id="policy.eu.dsa.platform",
    title="EU Digital Services Act (Reg (EU) 2022/2065) as a full platform-obligations policy",
    case_kind="policy",
    source_text=_SOURCE,
    question=("Understood as a whole-instrument platform-obligations policy: who "
              "does the DSA govern, under what conditions, with what consequence, "
              "through what procedure, for what purpose, and with what gaps?"),
    expected_terminal=Terminal.ESCALATE,  # OPEN causal/presupposed nodes dominate the fold
    tempting_answer=("this platform is a fully-compliant VLOP; its systemic risks "
                     "are identified and its mitigation measures are effective, so "
                     "no further obligation is open"),
    stages=(
        # ── structural — the intermediary is-a taxonomy (grounded, reachable) ───
        # the headline MULTI-HOP node: vlop → online_platform → hosting → intermediary
        StructuralCondition(
            name="vlop-is-a-intermediary-service",
            grounding=Grounding.span("vlop-is-a-intermediary-service",
                                     "Art 3(g)/(i) / Art 33"),
            warrant="a VLOP reaches the intermediary root over a stated is-a chain",
            subject="vlop", object="intermediary_service",
            edges=[is_a("vlop", "online_platform"),
                   is_a("online_platform", "hosting_service"),
                   is_a("hosting_service", "intermediary_service")],
        ),
        StructuralCondition(
            name="online-platform-is-a-hosting-service",
            grounding=Grounding.span("online-platform-is-a-hosting-service", "Art 3(i)"),
            warrant="Art 3(i): an online platform is a hosting service that "
                    "disseminates to the public — a stated is-a edge",
            subject="online_platform", object="hosting_service",
            edges=[is_a("online_platform", "hosting_service")],
        ),
        StructuralCondition(
            name="hosting-service-is-a-intermediary-service",
            grounding=Grounding.span("hosting-service-is-a-intermediary-service",
                                     "Art 3(g)(iii)"),
            warrant="Art 3(g)(iii): hosting is one intermediary sub-type",
            subject="hosting_service", object="intermediary_service",
            edges=[is_a("hosting_service", "intermediary_service")],
        ),
        StructuralCondition(
            name="mere-conduit-is-a-intermediary-service",
            grounding=Grounding.span("mere-conduit-is-a-intermediary-service",
                                     "Art 3(g)(i)"),
            warrant="Art 3(g)(i): mere conduit is a stated intermediary sub-type",
            subject="mere_conduit", object="intermediary_service",
            edges=[is_a("mere_conduit", "intermediary_service")],
        ),
        StructuralCondition(
            name="caching-is-a-intermediary-service",
            grounding=Grounding.span("caching-is-a-intermediary-service",
                                     "Art 3(g)(ii)"),
            warrant="Art 3(g)(ii): caching is a stated intermediary sub-type",
            subject="caching", object="intermediary_service",
            edges=[is_a("caching", "intermediary_service")],
        ),
        StructuralCondition(
            name="online-search-engine-classification",
            grounding=Grounding.span("online-search-engine-classification",
                                     "Art 3(j) / Art 33"),
            warrant="Art 3(j)/Art 33: the VLOSE branch — a very large online "
                    "search engine is a stated online-search-engine sub-type",
            subject="vlose", object="online_search_engine",
            edges=[is_a("vlose", "online_search_engine")],
        ),
        # the one honestly-closable defined term — backs definition_closure below
        StructuralCondition(
            name="recipient-of-the-service",
            grounding=Grounding.span("recipient-of-the-service", "Art 3(b)"),
            warrant="Art 3(b): 'any natural or legal person who uses the service' "
                    "reduces to a stated primitive membership test",
            subject="recipient_of_the_service", object="service_user",
            edges=[is_a("recipient_of_the_service", "service_user")],
        ),
        StructuralCondition(
            name="illegal-content-definition-structure",
            grounding=Grounding.gap(
                "illegal-content-definition-structure",
                "Art 3(h): 'illegal content' is defined BY REFERENCE to Union or "
                "member-state law — the definitional structure points outward and "
                "does not close within the policy; definition-closure NEEDS-BUILDING"),
            warrant="the term resolves only into an external legal corpus, unreachable here",
            subject="illegal_content", object="closed_primitive_set",
            edges=[], incomplete_nodes=["illegal_content"],  # unreachable + incomplete → OPEN
        ),
        StructuralCondition(
            name="systemic-risk-definition-structure",
            grounding=Grounding.gap(
                "systemic-risk-definition-structure",
                "Art 34 enumerates risk CATEGORIES but the term has no structural "
                "resolution to primitives — the categories are open evaluative headings"),
            warrant="an evaluative heading has no closed primitive resolution",
            subject="systemic_risk", object="closed_primitive_set",
            edges=[], incomplete_nodes=["systemic_risk"],
        ),
        StructuralCondition(
            name="definition-closure-to-primitives",
            grounding=Grounding.gap(
                "definition-closure-to-primitives",
                "recursive term→primitive closure is NEEDS-BUILDING (§8.2); DSA "
                "terms are defined via other undefined terms ('dissemination to the "
                "public', 'active recipient')"),
            warrant="recursive closure over undefined sub-terms is not textually complete",
            subject="dissemination_to_the_public", object="closed_primitive_set",
            edges=[], incomplete_nodes=["dissemination_to_the_public"],
        ),
        # ── causal — the systemic-risk → mitigation model (THINNEST GAP → OPEN) ──
        HonestGap(
            name="service-design-causes-systemic-risk", dimension="causal",
            grounding=Grounding.gap("service-design-causes-systemic-risk",
                                    "Art 34: the causal link from the platform's "
                                    "design/functioning to a systemic risk is "
                                    "presupposed, never modelled"),
            warrant="a causal design→risk model the DSA references but never states",
            reason_text="causal-model construction not in panel scope",
        ),
        HonestGap(
            name="recommender-system-amplifies-illegal-content", dimension="causal",
            grounding=Grounding.gap("recommender-system-amplifies-illegal-content",
                                    "Art 34(1)(a)/(2): the amplification pathway is "
                                    "a contested causal claim, unmodelled"),
            warrant="the amplification pathway is a presupposed causal claim",
            reason_text="causal amplification modelling not in panel scope",
        ),
        EpistemicPremise(
            name="systemic-risk-to-fundamental-rights", dimension="causal",
            grounding=Grounding.gap("systemic-risk-to-fundamental-rights",
                                    "Art 34(1)(b): the causal chain service→harm-to-"
                                    "Charter-rights is presupposed on the facts"),
            warrant="a presupposed causal chain to rights-harm cannot be rested on",
            status=EpistemicStatus.PRESUPPOSED,  # → OPEN
        ),
        HonestGap(
            name="systemic-risk-to-civic-discourse-and-elections", dimension="causal",
            grounding=Grounding.gap("systemic-risk-to-civic-discourse-and-elections",
                                    "Art 34(1)(c): the effect on civic discourse / "
                                    "electoral processes is a causal judgement the "
                                    "policy assumes"),
            warrant="a presupposed causal effect on civic discourse",
            reason_text="causal reasoning over civic-discourse effects not in panel scope",
        ),
        EpistemicPremise(
            name="systemic-risk-to-minors-and-wellbeing", dimension="causal",
            grounding=Grounding.gap("systemic-risk-to-minors-and-wellbeing",
                                    "Art 34(1)(d): the harm-to-minors pathway is "
                                    "presupposed, not established"),
            warrant="a presupposed causal pathway to minor-harm cannot be rested on",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        HonestGap(
            name="mitigation-measure-reduces-risk", dimension="causal",
            grounding=Grounding.gap("mitigation-measure-reduces-risk",
                                    "Art 35: that a mitigation CAUSALLY reduces the "
                                    "identified risk is asserted, not demonstrated — "
                                    "the core causal cell the layer must not fabricate"),
            warrant="a presupposed mitigation→risk-reduction cell",
            reason_text="mitigation-effectiveness causal modelling not in panel scope",
        ),
        HonestGap(
            name="crisis-mechanism-causes-mitigation", dimension="causal",
            grounding=Grounding.gap("crisis-mechanism-causes-mitigation",
                                    "Art 36: the crisis-response causal loop "
                                    "(trigger→measure→reduced-harm) is presupposed"),
            warrant="a presupposed crisis-response causal loop",
            reason_text="crisis-loop causal modelling not in panel scope",
        ),
        # ── temporal — reporting cadences / compliance windows (grounded order) ──
        TemporalOrder(
            name="transparency-report-annual-cadence",
            grounding=Grounding.span("transparency-report-annual-cadence",
                                     "Art 15 / Art 24"),
            warrant="first annual transparency report due date precedes today → cadence open",
            op="on_or_before", left="2024-02-17", right=_T,
        ),
        TemporalOrder(
            name="active-recipient-count-six-monthly",
            grounding=Grounding.span("active-recipient-count-six-monthly", "Art 24(2)"),
            warrant="first six-monthly active-recipient publication due 2023-02-17 → past",
            op="on_or_before", left="2023-02-17", right=_T,
        ),
        TemporalOrder(
            name="vlop-risk-assessment-annual",
            grounding=Grounding.span("vlop-risk-assessment-annual", "Art 34(1)"),
            warrant="first VLOP annual risk assessment due 2023-08-25 → past → cadence open",
            op="on_or_before", left="2023-08-25", right=_T,
        ),
        TemporalOrder(
            name="independent-audit-annual",
            grounding=Grounding.span("independent-audit-annual", "Art 37"),
            warrant="first VLOP annual independent audit due 2024-08-25 → past",
            op="on_or_before", left="2024-08-25", right=_T,
        ),
        TemporalOrder(
            name="vlop-designation-four-month-compliance-window",
            grounding=Grounding.span("vlop-designation-four-month-compliance-window",
                                     "Art 33(6)"),
            warrant="VLOP obligations apply four months after designation (first "
                    "wave 2023-08-25) → window open at T",
            op="on_or_before", left="2023-08-25", right=_T,
        ),
        TemporalOrder(
            name="statement-of-reasons-timing",
            grounding=Grounding.gap("statement-of-reasons-timing",
                                    "Art 17: a statement of reasons is due but the "
                                    "operative timing is open-textured and "
                                    "presupposed per case"),
            warrant="the operative per-case deadline is presupposed, not stated → OPEN",
            op="on_or_before", left=None, right=_T,  # unresolved operand → OPEN
        ),
        TemporalOrder(
            name="notice-acknowledgement-and-decision-timeliness",
            grounding=Grounding.gap("notice-acknowledgement-and-decision-timeliness",
                                    "Art 16: notices handled 'in a timely, diligent, "
                                    "non-arbitrary' manner — the concrete deadline is "
                                    "presupposed, not fixed"),
            warrant="the concrete notice deadline is presupposed → OPEN",
            op="on_or_before", left=None, right=_T,
        ),
        TemporalOrder(
            name="crisis-response-period",
            grounding=Grounding.gap("crisis-response-period",
                                    "Art 36: crisis-response measures run for a "
                                    "Commission-set period the policy references but "
                                    "does not fix"),
            warrant="the crisis-response period is Commission-set and presupposed → OPEN",
            op="on_or_before", left=None, right=_T,
        ),
        # ── relational — the tiered actor value-chain ───────────────────────────
        IntentionalCondition(
            name="provider-recipient-of-service-link", dimension="relational",
            grounding=Grounding.span("provider-recipient-of-service-link", "Art 3(b)"),
            warrant="Art 3(b): the provider→recipient relation is stated",
            literal="provider_recipient_relation",
            present=["provider_recipient_relation"],
        ),
        IntentionalCondition(
            name="notice-provider-to-hosting-service-link", dimension="relational",
            grounding=Grounding.span("notice-provider-to-hosting-service-link", "Art 16"),
            warrant="Art 16: the notice-and-action channel from a notifier to the "
                    "hosting provider is a stated relation",
            literal="notice_to_hosting_relation",
            present=["notice_to_hosting_relation"],
        ),
        IntentionalCondition(
            name="provider-to-legal-representative-link", dimension="relational",
            grounding=Grounding.span("provider-to-legal-representative-link", "Art 13"),
            warrant="Art 13: a provider without EU establishment designates a legal "
                    "representative — a stated linkage",
            literal="provider_legal_representative_relation",
            present=["provider_legal_representative_relation"],
        ),
        IntentionalCondition(
            name="provider-to-digital-services-coordinator-link", dimension="relational",
            grounding=Grounding.span("provider-to-digital-services-coordinator-link",
                                     "Art 49-51"),
            warrant="Art 49-51: the provider→competent-DSC supervisory relation, stated",
            literal="provider_dsc_relation",
            present=["provider_dsc_relation"],
        ),
        IntentionalCondition(
            name="vlop-to-commission-supervision-link", dimension="relational",
            grounding=Grounding.span("vlop-to-commission-supervision-link", "Art 56"),
            warrant="Art 56: enhanced Commission supervision of VLOPs — a stated relation",
            literal="vlop_commission_relation",
            present=["vlop_commission_relation"],
        ),
        IntentionalCondition(
            name="recommender-to-recipient-parameter-link", dimension="relational",
            grounding=Grounding.span("recommender-to-recipient-parameter-link", "Art 27"),
            warrant="Art 27: the main-parameter disclosure relation between the "
                    "recommender system and the recipient, stated",
            literal="recommender_recipient_relation",
            present=["recommender_recipient_relation"],
        ),
        IntentionalCondition(
            name="advertiser-to-platform-transparency-link", dimension="relational",
            grounding=Grounding.span("advertiser-to-platform-transparency-link", "Art 26"),
            warrant="Art 26: the online-advertising transparency relation, stated",
            literal="advertiser_platform_relation",
            present=["advertiser_platform_relation"],
        ),
        EpistemicPremise(
            name="trusted-flagger-designation-link", dimension="relational",
            grounding=Grounding.gap("trusted-flagger-designation-link",
                                    "Art 22: trusted-flagger STATUS is awarded by a "
                                    "Digital Services Coordinator — whether a given "
                                    "entity holds it is a presupposed designation act"),
            warrant="the trusted-flagger designation is an external act, presupposed",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        HonestGap(
            name="out-of-court-dispute-body-certification-link", dimension="relational",
            grounding=Grounding.gap("out-of-court-dispute-body-certification-link",
                                    "Art 21: an out-of-court dispute-settlement body "
                                    "must be CERTIFIED by a DSC — the certification is "
                                    "presupposed per body"),
            warrant="the dispute-body certification is an external act, presupposed",
            reason_text="per-body certification status not in panel scope",
        ),
        HonestGap(
            name="joint-provider-establishment-country-of-origin", dimension="relational",
            grounding=Grounding.gap("joint-provider-establishment-country-of-origin",
                                    "which member state is the country of establishment "
                                    "(and hence lead DSC) for a concrete provider is "
                                    "presupposed, not stated"),
            warrant="the country-of-establishment fact is presupposed",
            reason_text="country-of-origin attribution not in panel scope",
        ),
        # ── intentional — the platform obligations + purposes (deontic half) ─────
        IntentionalCondition(
            name="notice-and-action-obligation",
            grounding=Grounding.span("notice-and-action-obligation", "Art 16"),
            warrant="Art 16: hosting providers must operate notice-and-action mechanisms",
            literal="notice_and_action_duty",
            present=["notice_and_action_duty"],
        ),
        IntentionalCondition(
            name="statement-of-reasons-obligation",
            grounding=Grounding.span("statement-of-reasons-obligation", "Art 17"),
            warrant="Art 17: a clear statement of reasons for each content restriction",
            literal="statement_of_reasons_duty",
            present=["statement_of_reasons_duty"],
        ),
        IntentionalCondition(
            name="illegal-content-expeditious-removal-duty",
            grounding=Grounding.span("illegal-content-expeditious-removal-duty", "Art 6"),
            warrant="Art 6: the hosting liability exemption is conditioned on acting "
                    "expeditiously upon awareness — a stated duty",
            literal="expeditious_removal_duty",
            present=["expeditious_removal_duty"],
        ),
        IntentionalCondition(
            name="trusted-flagger-priority-obligation",
            grounding=Grounding.span("trusted-flagger-priority-obligation", "Art 22"),
            warrant="Art 22: notices from trusted flaggers processed with priority",
            literal="trusted_flagger_priority_duty",
            present=["trusted_flagger_priority_duty"],
        ),
        IntentionalCondition(
            name="transparency-reporting-obligation",
            grounding=Grounding.span("transparency-reporting-obligation",
                                     "Art 15 / 24 / 42"),
            warrant="Art 15/24/42: the duty to publish transparency reports — stated",
            literal="transparency_reporting_duty",
            present=["transparency_reporting_duty"],
        ),
        IntentionalCondition(
            name="recommender-transparency-obligation",
            grounding=Grounding.span("recommender-transparency-obligation",
                                     "Art 27 / Art 38"),
            warrant="Art 27 (+ Art 38 non-profiling option for VLOPs): main-parameter "
                    "disclosure — stated",
            literal="recommender_transparency_duty",
            present=["recommender_transparency_duty"],
        ),
        IntentionalCondition(
            name="internal-complaint-and-redress-duty",
            grounding=Grounding.span("internal-complaint-and-redress-duty", "Art 20 / 21"),
            warrant="Art 20/21: internal complaint-handling + out-of-court dispute route",
            literal="complaint_and_redress_duty",
            present=["complaint_and_redress_duty"],
        ),
        IntentionalCondition(
            name="purpose-safe-predictable-trusted-environment",
            grounding=Grounding.span("purpose-safe-predictable-trusted-environment", "Art 1"),
            warrant="Art 1: a safe, predictable and trusted online environment and "
                    "protection of fundamental rights — a grounded teleology node",
            literal="safe_trusted_environment_purpose",
            present=["safe_trusted_environment_purpose"],
        ),
        HonestGap(
            name="risk-mitigation-obligation", dimension="intentional",
            grounding=Grounding.gap("risk-mitigation-obligation",
                                    "Art 35: VLOPs must put in place 'reasonable, "
                                    "proportionate and effective' mitigation — the "
                                    "obligation's operative content is open-textured "
                                    "and its discharge presupposed, not established"),
            warrant="the operative mitigation content is presupposed, not established",
            reason_text="open-textured mitigation discharge not in panel scope",
        ),
        EpistemicPremise(
            name="risk-mitigation-effectiveness-judgement", dimension="intentional",
            grounding=Grounding.gap("risk-mitigation-effectiveness-judgement",
                                    "Art 35: that a chosen mitigation is EFFECTIVE "
                                    "against the identified risk is an evaluative "
                                    "judgement the policy asserts but never demonstrates"),
            warrant="a presupposed effectiveness judgement cannot be rested on",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        DeonticResolution(
            name="removal-order-vs-fundamental-rights-collision",
            grounding=Grounding.gap("removal-order-vs-fundamental-rights-collision",
                                    "a member-state removal order (Art 9) collides "
                                    "with an Art 14 fundamental-rights limit on the "
                                    "same act, no stated ordering → genuine collision"),
            warrant="two contradictory norms on the same act, no ordering → escalate",
            norms=[("remove_content", "obligatory", "member_state_removal_order_art9"),
                   ("remove_content", "prohibited", "fundamental_rights_limit_art14")],
            act="remove_content", pack="generic",  # collision → OPEN
        ),
        # ── nD — governance meta-norms ──────────────────────────────────────────
        IntentionalCondition(
            name="proportionality-of-obligations-to-tier", dimension="nD",
            grounding=Grounding.span("proportionality-of-obligations-to-tier",
                                     "Chapter III / Art 33"),
            warrant="the DSA's asymmetric design meta-norm: obligations scale by "
                    "role (intermediary < hosting < platform < VLOP) — stated",
            literal="asymmetric_tiered_obligations",
            present=["asymmetric_tiered_obligations"],
        ),
        IntentionalCondition(
            name="country-of-origin-supervision-principle", dimension="nD",
            grounding=Grounding.span("country-of-origin-supervision-principle", "Art 56"),
            warrant="Art 56: the establishment-based allocation of supervisory "
                    "competence — a stated meta-norm",
            literal="country_of_origin_supervision",
            present=["country_of_origin_supervision"],
        ),
        IntentionalCondition(
            name="commission-exclusive-supervision-of-vlops", dimension="nD",
            grounding=Grounding.span("commission-exclusive-supervision-of-vlops",
                                     "Art 56(2)"),
            warrant="Art 56(2): the Commission's exclusive enforcement powers over "
                    "VLOP-specific obligations — stated",
            literal="commission_exclusive_vlop_supervision",
            present=["commission_exclusive_vlop_supervision"],
        ),
        IntentionalCondition(
            name="penalty-ceiling-six-percent-turnover", dimension="nD",
            grounding=Grounding.span("penalty-ceiling-six-percent-turnover", "Art 74"),
            warrant="Art 74: fines up to 6% of annual worldwide turnover — a stated "
                    "meta-norm on sanction",
            literal="penalty_ceiling_six_percent",
            present=["penalty_ceiling_six_percent"],
        ),
        IntentionalCondition(
            name="board-cross-border-cooperation", dimension="nD",
            grounding=Grounding.span("board-cross-border-cooperation", "Art 61-63"),
            warrant="Art 61-63: the European Board for Digital Services coordination "
                    "mechanism — stated",
            literal="board_cross_border_cooperation",
            present=["board_cross_border_cooperation"],
        ),
        HonestGap(
            name="delegated-and-implementing-acts-standard-setting", dimension="nD",
            grounding=Grounding.gap("delegated-and-implementing-acts-standard-setting",
                                    "Art 87: operative detail (audit methodology, "
                                    "data-access standards) is deferred to future "
                                    "delegated/implementing acts the policy references "
                                    "but does not contain"),
            warrant="delegated substantive content is under-determined",
            reason_text="delegated-content resolution not in panel scope",
        ),
        HonestGap(
            name="governance-override-when-regimes-conflict", dimension="nD",
            grounding=Grounding.gap("governance-override-when-regimes-conflict",
                                    "how the policy resolves a conflict with another "
                                    "binding regime (e.g. a member-state removal order "
                                    "vs a fundamental-rights limit) is presupposed"),
            warrant="the cross-regime override rule is presupposed",
            reason_text="cross-regime conflict resolution not in panel scope",
        ),
    ),
    expected_subgraph=(
        # structural
        NodeExpectation("structural", "vlop-is-a-intermediary-service", Verdict.SATISFIED),
        NodeExpectation("structural", "online-platform-is-a-hosting-service", Verdict.SATISFIED),
        NodeExpectation("structural", "hosting-service-is-a-intermediary-service", Verdict.SATISFIED),
        NodeExpectation("structural", "mere-conduit-is-a-intermediary-service", Verdict.SATISFIED),
        NodeExpectation("structural", "caching-is-a-intermediary-service", Verdict.SATISFIED),
        NodeExpectation("structural", "online-search-engine-classification", Verdict.SATISFIED),
        NodeExpectation("structural", "recipient-of-the-service", Verdict.SATISFIED),
        NodeExpectation("structural", "illegal-content-definition-structure", Verdict.OPEN),
        NodeExpectation("structural", "systemic-risk-definition-structure", Verdict.OPEN),
        NodeExpectation("structural", "definition-closure-to-primitives", Verdict.OPEN),
        # causal (all OPEN — thinnest gap)
        NodeExpectation("causal", "service-design-causes-systemic-risk", Verdict.OPEN),
        NodeExpectation("causal", "recommender-system-amplifies-illegal-content", Verdict.OPEN),
        NodeExpectation("causal", "systemic-risk-to-fundamental-rights", Verdict.OPEN),
        NodeExpectation("causal", "systemic-risk-to-civic-discourse-and-elections", Verdict.OPEN),
        NodeExpectation("causal", "systemic-risk-to-minors-and-wellbeing", Verdict.OPEN),
        NodeExpectation("causal", "mitigation-measure-reduces-risk", Verdict.OPEN),
        NodeExpectation("causal", "crisis-mechanism-causes-mitigation", Verdict.OPEN),
        # temporal
        NodeExpectation("temporal", "transparency-report-annual-cadence", Verdict.SATISFIED),
        NodeExpectation("temporal", "active-recipient-count-six-monthly", Verdict.SATISFIED),
        NodeExpectation("temporal", "vlop-risk-assessment-annual", Verdict.SATISFIED),
        NodeExpectation("temporal", "independent-audit-annual", Verdict.SATISFIED),
        NodeExpectation("temporal", "vlop-designation-four-month-compliance-window", Verdict.SATISFIED),
        NodeExpectation("temporal", "statement-of-reasons-timing", Verdict.OPEN),
        NodeExpectation("temporal", "notice-acknowledgement-and-decision-timeliness", Verdict.OPEN),
        NodeExpectation("temporal", "crisis-response-period", Verdict.OPEN),
        # relational
        NodeExpectation("relational", "provider-recipient-of-service-link", Verdict.SATISFIED),
        NodeExpectation("relational", "notice-provider-to-hosting-service-link", Verdict.SATISFIED),
        NodeExpectation("relational", "provider-to-legal-representative-link", Verdict.SATISFIED),
        NodeExpectation("relational", "provider-to-digital-services-coordinator-link", Verdict.SATISFIED),
        NodeExpectation("relational", "vlop-to-commission-supervision-link", Verdict.SATISFIED),
        NodeExpectation("relational", "recommender-to-recipient-parameter-link", Verdict.SATISFIED),
        NodeExpectation("relational", "advertiser-to-platform-transparency-link", Verdict.SATISFIED),
        NodeExpectation("relational", "trusted-flagger-designation-link", Verdict.OPEN),
        NodeExpectation("relational", "out-of-court-dispute-body-certification-link", Verdict.OPEN),
        NodeExpectation("relational", "joint-provider-establishment-country-of-origin", Verdict.OPEN),
        # intentional
        NodeExpectation("intentional", "notice-and-action-obligation", Verdict.SATISFIED),
        NodeExpectation("intentional", "statement-of-reasons-obligation", Verdict.SATISFIED),
        NodeExpectation("intentional", "illegal-content-expeditious-removal-duty", Verdict.SATISFIED),
        NodeExpectation("intentional", "trusted-flagger-priority-obligation", Verdict.SATISFIED),
        NodeExpectation("intentional", "transparency-reporting-obligation", Verdict.SATISFIED),
        NodeExpectation("intentional", "recommender-transparency-obligation", Verdict.SATISFIED),
        NodeExpectation("intentional", "internal-complaint-and-redress-duty", Verdict.SATISFIED),
        NodeExpectation("intentional", "purpose-safe-predictable-trusted-environment", Verdict.SATISFIED),
        NodeExpectation("intentional", "risk-mitigation-obligation", Verdict.OPEN),
        NodeExpectation("intentional", "risk-mitigation-effectiveness-judgement", Verdict.OPEN),
        NodeExpectation("intentional", "removal-order-vs-fundamental-rights-collision", Verdict.OPEN),
        # nD
        NodeExpectation("nD", "proportionality-of-obligations-to-tier", Verdict.SATISFIED),
        NodeExpectation("nD", "country-of-origin-supervision-principle", Verdict.SATISFIED),
        NodeExpectation("nD", "commission-exclusive-supervision-of-vlops", Verdict.SATISFIED),
        NodeExpectation("nD", "penalty-ceiling-six-percent-turnover", Verdict.SATISFIED),
        NodeExpectation("nD", "board-cross-border-cooperation", Verdict.SATISFIED),
        NodeExpectation("nD", "delegated-and-implementing-acts-standard-setting", Verdict.OPEN),
        NodeExpectation("nD", "governance-override-when-regimes-conflict", Verdict.OPEN),
    ),
    definition_closure={
        # honest: recursive definition-closure is NEEDS-BUILDING (§8.2). Only
        # recipient-of-the-service is backed by a same-named SATISFIED structural
        # stage; every other core term stays OPEN (an honest pass) — above all
        # 'systemic-risk' and 'illegal-content', which cannot close within the policy.
        "recipient-of-the-service": "resolves_to_primitives",
        "intermediary-service": "OPEN",
        "online-platform": "OPEN",
        "vlop": "OPEN",
        "illegal-content": "OPEN",
        "systemic-risk": "OPEN",
        "trusted-flagger": "OPEN",
        "active-recipient-of-the-service": "OPEN",
    },
    understand_bar=UnderstandBar(
        who_what=("Providers of intermediary services offered to recipients in the "
                  "Union — tiered mere-conduit / caching / hosting / online platform "
                  "/ VLOP (plus the VLOSE branch) — with the recipients, notifiers, "
                  "trusted flaggers, dispute bodies, DSCs and the Commission linked "
                  "to them. The is-a taxonomy and the actor value-chain are grounded. "
                  "OPEN: whether a CONCRETE provider is a VLOP (the threshold count) "
                  "or a CONCRETE entity is a designated trusted flagger is presupposed."),
        conditions=("Obligations attach by tier: hosting triggers notice-and-action "
                    "+ statement of reasons; online-platform adds recommender "
                    "transparency, complaint-handling and out-of-court dispute; VLOP "
                    "adds annual systemic-risk assessment, mitigation and audit. "
                    "OPEN: that a service crosses the 45M VLOP threshold and that a "
                    "piece of content IS illegal under some law are presupposed."),
        consequence=("Breach exposes the provider to supervisory action and fines up "
                     "to 6% of worldwide annual turnover (Art 74), and — for VLOPs — "
                     "enhanced Commission enforcement. OPEN: the causal systemic-risk "
                     "model that scales VLOP consequences (design→risk→mitigation) is "
                     "presupposed, not modelled."),
        procedure=("Notice-and-action (Art 16) with a reasoned statement (Art 17); "
                   "internal complaint-handling (Art 20) + certified out-of-court "
                   "dispute (Art 21); ANNUAL transparency reports (Art 15/24), "
                   "SIX-MONTHLY active-recipient figures (Art 24(2)), ANNUAL VLOP "
                   "risk assessment (Art 34) and audit (Art 37) within a FOUR-MONTH "
                   "post-designation window (Art 33(6)). OPEN: concrete per-notice "
                   "and per-crisis deadlines."),
        purpose=("Art 1: to secure a safe, predictable and trusted online environment "
                 "and to protect the fundamental rights enshrined in the Charter."),
        gaps=("OPEN: (1) the entire causal systemic-risk→mitigation→effectiveness "
              "model (§8.2 causal gap); (2) whether a service crosses the 45M VLOP "
              "threshold; (3) whether specific content is 'illegal' under the "
              "applicable law; (4) whether an entity is a designated trusted flagger "
              "/ certified dispute body; (5) the country of establishment fixing the "
              "lead DSC; (6) operative per-notice/per-crisis timing; (7) recursive "
              "definition-closure of 'systemic risk', 'illegal content', "
              "'dissemination to the public'."),
    ),
    presupposed_probes=(
        PresupposedProbe(
            "service crosses the 45M VLOP threshold (Art 33)", Terminal.ESCALATE),
        PresupposedProbe(
            "flagged content is 'illegal content' under applicable law (Art 3(h))",
            Terminal.ESCALATE),
        PresupposedProbe(
            "the adopted mitigation is 'effective' against the risk (Art 35)",
            Terminal.ESCALATE),
        PresupposedProbe(
            "the claimant entity holds trusted-flagger status (Art 22)",
            Terminal.ESCALATE),
    ),
    probes=(
        Probe(
            kind="genuine_collision",
            note="a member-state removal order (Art 9) vs an Art 14 fundamental-rights limit",
            stages=(DeonticResolution(
                name="removal_order_collision",
                grounding=Grounding.span("removal_order_collision", "Art 9 vs Art 14"),
                warrant="two contradictory norms on the same act, no ordering",
                norms=[("remove_content", "obligatory", "member_state_removal_order_art9"),
                       ("remove_content", "prohibited", "fundamental_rights_limit_art14")],
                act="remove_content", pack="generic"),),
        ),
        Probe(
            kind="presupposed_fact",
            note="a service's VLOP status is presupposed knowable from the threshold count",
            stages=(EpistemicPremise(
                name="vlop_threshold_presupposed",
                grounding=Grounding.gap("vlop_threshold_presupposed",
                                        "the 45M active-recipient count is presupposed, "
                                        "not established"),
                warrant="a presupposed threshold-founding count cannot be rested on",
                status=EpistemicStatus.PRESUPPOSED),),
        ),
        Probe(
            kind="unsettled_reading",
            note="whether the Art 6 'expeditious action' liability carve-out applies",
            stages=(EpistemicPremise(
                name="expeditious_action_unsettled",
                grounding=Grounding.gap("expeditious_action_unsettled",
                                        "the carve-out's application is contested"),
                warrant="a contested reading is a human's call, not the engine's",
                status=EpistemicStatus.CONTESTED),),
        ),
    ),
)
