# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Policy case — a GDPR-grounded organisational Data-Protection / Privacy Policy.

The whole-document governance view of a controller-side data-protection policy
(nD meta-norms, controller/processor roles, lawful bases, retention, the breach
clock, DSAR deadlines, DPO spine), NOT a narrow Art-by-Art statute question.
§8.1 STRUCTURED expectation: a 5D+nD subgraph, a definition-closure map, the
six-answer understand-bar, and presupposed-fact probes.

Honesty posture (§8.2): the norm/deontic half is BUILT → the grounded deontic,
structural-taxonomy, temporal-deadline and governance-spine nodes compute
SATISFIED; the factual half — above all the CAUSAL risk-to-rights model and the
presupposed world-facts (a *valid* lawful basis for a concrete activity, a
transfer destination's adequacy, a processor's actual Art 28 compliance) — is
NEEDS-BUILDING → those nodes are OPEN (a first-class PASS), never fabricated. The
fold is OPEN-dominant, so the whole-policy terminal is honestly ESCALATE: a
well-drafted policy is *grounded* where it states things yet cannot close to
DETERMINATE ("compliant") while its world-model rests on presupposition.
Grounded != verified.

Every node's verdict is COMPUTED by a real evaluator (structural reachability,
closed-world literal, date order, duration threshold, epistemic settledness,
deontic resolution, or an explicit HonestGap), then graded against the
expectation below — never hand-set.
"""
from __future__ import annotations

from ... import (
    CaseSpec, DeonticResolution, EpistemicPremise, EpistemicStatus, Grounding,
    HonestGap, IntentionalCondition, NodeExpectation, PresupposedProbe, Probe,
    QuantThreshold, StructuralCondition, TemporalOrder, Terminal, UnderstandBar,
    Verdict, duration, is_a,
)

# Today, as a fixed fact of the case (deterministic — never Date.now()).
_T = "2026-08-06"
# GDPR became applicable on this date — the temporal floor for "duty in force".
_APP = "2018-05-25"

_SOURCE = (
    "Organisational Data-Protection / Privacy Policy grounded in the GDPR "
    "(Regulation (EU) 2016/679). Art 4: definitions (personal data, processing, "
    "controller, processor). Art 5: principles (purpose limitation, "
    "minimisation, storage limitation, accountability). Art 6: lawful bases. "
    "Art 7: conditions for consent. Art 9: special categories. Art 12-22: "
    "data-subject rights and the one-month response deadline. Art 24/25/32: "
    "controller responsibility, data protection by design, security of "
    "processing (appropriate technical and organisational measures). Art 26: "
    "joint controllers. Art 28: processor contracts and sub-processors. Art 30: "
    "records of processing activities. Art 33: breach notification to the "
    "supervisory authority within 72 hours. Art 34: communication to data "
    "subjects. Art 35: data protection impact assessment. Art 37-39: the data "
    "protection officer. Art 44-49: international transfers and adequacy. "
    "Art 56: the lead supervisory authority. Art 83: administrative fines."
)


CASE = CaseSpec(
    id="policy.eu.gdpr.data_protection",
    title="GDPR organisational Data-Protection / Privacy Policy (controller-side)",
    case_kind="policy",
    source_text=_SOURCE,
    question=("Understood as a whole-document data-protection policy: who / what "
              "does it govern, under what conditions, with what consequence, "
              "through what procedure, for what purpose, and with what gaps — "
              "grounded where stated and OPEN where presupposed?"),
    expected_terminal=Terminal.ESCALATE,  # OPEN causal/presupposed nodes dominate the fold
    tempting_answer=("the organisation is fully GDPR-compliant; every processing "
                     "activity has a valid lawful basis and all safeguards are "
                     "adequate, so the policy resolves determinately"),
    stages=(
        # ── structural — ontology / definitions / document anatomy ──────────────
        StructuralCondition(
            name="policy-scope-personal-data-defined",
            grounding=Grounding.span("policy-scope-personal-data-defined", "Art 4(1)"),
            warrant="the policy restates 'personal data' as a stated ontology node",
            subject="personal_data", object="regulated_datum",
            edges=[is_a("personal_data", "regulated_datum")],
        ),
        StructuralCondition(
            name="policy-scope-processing-defined",
            grounding=Grounding.span("policy-scope-processing-defined", "Art 4(2)"),
            warrant="'processing' enumerated in the policy's definitions section",
            subject="processing_operation", object="regulated_operation",
            edges=[is_a("processing_operation", "regulated_operation")],
        ),
        StructuralCondition(
            name="special-category-data-carveout",
            grounding=Grounding.span("special-category-data-carveout", "Art 9(1)"),
            warrant="Art 9 special categories are a stated sub-kind of personal data",
            subject="special_category_data", object="personal_data",
            edges=[is_a("special_category_data", "personal_data")],
        ),
        StructuralCondition(
            name="records-of-processing-inventory",
            grounding=Grounding.span("records-of-processing-inventory", "Art 30"),
            warrant="the Art 30 ROPA is a stated documented inventory node",
            subject="processing_activities_register", object="documented_inventory",
            edges=[is_a("processing_activities_register", "documented_inventory")],
        ),
        # the honestly-closable defined terms — back definition_closure below
        StructuralCondition(
            name="processing",
            grounding=Grounding.span("processing", "Art 4(2)"),
            warrant="Art 4(2) is a closed disjunction over primitive operations "
                    "(collection, storage, erasure, …) — it bottoms out",
            subject="processing", object="enumerated_operation_set",
            edges=[is_a("processing", "enumerated_operation_set")],
        ),
        StructuralCondition(
            name="controller",
            grounding=Grounding.span("controller", "Art 4(7)"),
            warrant="'determines the purposes and means' reduces to two stated "
                    "primitives (purpose-determination, means-determination)",
            subject="controller", object="purpose_and_means_determiner",
            edges=[is_a("controller", "purpose_and_means_determiner")],
        ),
        StructuralCondition(
            name="processor",
            grounding=Grounding.span("processor", "Art 4(8)"),
            warrant="'processes on behalf of the controller' resolves against the "
                    "now-primitive processing + controller terms",
            subject="processor", object="on_behalf_processor",
            edges=[is_a("processor", "on_behalf_processor")],
        ),
        EpistemicPremise(
            name="special-category-lawful-condition-present", dimension="structural",
            grounding=Grounding.gap(
                "special-category-lawful-condition-present",
                "that an Art 9(2) condition ACTUALLY holds for a given special-"
                "category activity is presupposed, never established per activity"),
            warrant="a presupposed per-activity condition cannot be rested on",
            status=EpistemicStatus.PRESUPPOSED,  # → OPEN
        ),
        HonestGap(
            name="definition-closure-to-primitives", dimension="structural",
            grounding=Grounding.gap(
                "definition-closure-to-primitives",
                "recursive term->primitive closure is NEEDS-BUILDING (§8.2); the "
                "policy defines terms in terms of other undefined terms"),
            warrant="general recursive closure operation is not in panel scope",
            reason_text="recursive definition-closure not in panel scope",
        ),
        # ── causal — the THINNEST GAP → all OPEN (never fabricated) ─────────────
        HonestGap(
            name="processing-causes-risk-to-rights", dimension="causal",
            grounding=Grounding.gap(
                "processing-causes-risk-to-rights",
                "the causal link processing->risk-to-rights-and-freedoms is "
                "presupposed by Art 24/32/35 but never modelled"),
            warrant="a causal harm-model the policy references but never states",
            reason_text="causal-model construction not in panel scope",
        ),
        HonestGap(
            name="breach-likely-to-result-in-risk", dimension="causal",
            grounding=Grounding.gap(
                "breach-likely-to-result-in-risk",
                "the Art 33/34 'likely to result in a risk' causal judgement is "
                "contested and unmodelled → OPEN"),
            warrant="the breach-risk likelihood is a presupposed causal judgement",
            reason_text="causal likelihood evaluation not in panel scope",
        ),
        EpistemicPremise(
            name="dpia-high-risk-trigger", dimension="causal",
            grounding=Grounding.gap(
                "dpia-high-risk-trigger",
                "Art 35: whether processing is 'likely to result in a high risk' "
                "(the DPIA trigger) is a presupposed causal assessment"),
            warrant="a presupposed high-risk causal trigger cannot be rested on",
            status=EpistemicStatus.PRESUPPOSED,  # → OPEN
        ),
        HonestGap(
            name="safeguards-mitigate-risk", dimension="causal",
            grounding=Grounding.gap(
                "safeguards-mitigate-risk",
                "that technical/organisational measures CAUSALLY reduce the risk "
                "is asserted (Art 32), not demonstrated"),
            warrant="the mitigation's causal efficacy is presupposed",
            reason_text="causal mitigation modelling not in panel scope",
        ),
        # ── temporal — retention, the 72h clock, response deadlines (RICH) ──────
        QuantThreshold(
            name="breach-notify-authority-72h", dimension="temporal",
            grounding=Grounding.span("breach-notify-authority-72h", "Art 33(1)"),
            warrant="notification 48h after awareness is within the 72-hour bound",
            comparator="<=", value="72", unit="hours", operand=duration(hours=48),
        ),
        IntentionalCondition(
            name="breach-notify-data-subject-without-undue-delay", dimension="temporal",
            grounding=Grounding.span("breach-notify-data-subject-without-undue-delay",
                                     "Art 34(1)"),
            warrant="Art 34: high-risk breaches communicated without undue delay",
            literal="notify_data_subject_without_undue_delay",
            present=["notify_data_subject_without_undue_delay"],
        ),
        TemporalOrder(
            name="dsar-response-one-month",
            grounding=Grounding.span("dsar-response-one-month", "Art 12(3)"),
            warrant="the one-month DSAR response duty is in force at T",
            op="on_or_before", left=_APP, right=_T,
        ),
        IntentionalCondition(
            name="dsar-extension-two-months", dimension="temporal",
            grounding=Grounding.span("dsar-extension-two-months", "Art 12(3)"),
            warrant="Art 12(3): extendable by two further months for complex requests",
            literal="dsar_extension_two_months_stated",
            present=["dsar_extension_two_months_stated"],
        ),
        IntentionalCondition(
            name="retention-period-per-category-stated", dimension="temporal",
            grounding=Grounding.span("retention-period-per-category-stated",
                                     "Art 5(1)(e)"),
            warrant="the retention schedule assigns a defined period per category",
            literal="retention_schedule_per_category",
            present=["retention_schedule_per_category"],
        ),
        TemporalOrder(
            name="retention-clock-trigger-event",
            grounding=Grounding.gap(
                "retention-clock-trigger-event",
                "WHEN the retention clock starts (last-contact? contract-end?) is "
                "presupposed per record, not fixed by the text"),
            warrant="the operative trigger date is presupposed → OPEN",
            op="on_or_before", left=None, right=_T,  # unresolved operand → OPEN
        ),
        EpistemicPremise(
            name="erasure-on-expiry-executed", dimension="temporal",
            grounding=Grounding.gap(
                "erasure-on-expiry-executed",
                "that expired data is ACTUALLY deleted on schedule is a world-fact "
                "the policy asserts as a duty but does not establish as done"),
            warrant="a presupposed done-state cannot be rested on",
            status=EpistemicStatus.PRESUPPOSED,  # → OPEN
        ),
        IntentionalCondition(
            name="consent-withdrawal-effective-going-forward", dimension="temporal",
            grounding=Grounding.span("consent-withdrawal-effective-going-forward",
                                     "Art 7(3)"),
            warrant="Art 7(3): withdrawal as easy as giving; effective prospectively",
            literal="consent_withdrawal_prospective",
            present=["consent_withdrawal_prospective"],
        ),
        # ── relational — controller / processor / sub-processor / DPO chain ─────
        IntentionalCondition(
            name="controller-role-identified", dimension="relational",
            grounding=Grounding.span("controller-role-identified", "Art 4(7)"),
            warrant="the policy names the organisation as controller with contact",
            literal="controller_identity_stated",
            present=["controller_identity_stated"],
        ),
        IntentionalCondition(
            name="dpo-appointed-and-contactable", dimension="relational",
            grounding=Grounding.span("dpo-appointed-and-contactable", "Art 37-39"),
            warrant="the policy appoints a DPO and publishes the contact point",
            literal="dpo_appointed_contact_published",
            present=["dpo_appointed_contact_published"],
        ),
        IntentionalCondition(
            name="processor-engaged-under-art28-contract", dimension="relational",
            grounding=Grounding.span("processor-engaged-under-art28-contract",
                                     "Art 28(3)"),
            warrant="processors engaged only under a written data-processing agreement",
            literal="processor_under_art28_contract",
            present=["processor_under_art28_contract"],
        ),
        IntentionalCondition(
            name="sub-processor-authorisation-chain", dimension="relational",
            grounding=Grounding.span("sub-processor-authorisation-chain",
                                     "Art 28(2) / 28(4)"),
            warrant="sub-processors require prior authorisation and flow-down terms",
            literal="sub_processor_authorisation_and_flowdown",
            present=["sub_processor_authorisation_and_flowdown"],
        ),
        EpistemicPremise(
            name="joint-controller-arrangement", dimension="relational",
            grounding=Grounding.gap(
                "joint-controller-arrangement",
                "whether any relationship is IN FACT joint-controllership (Art 26) "
                "is presupposed; the policy names the possibility, not the concrete "
                "arrangement"),
            warrant="the concrete joint-controllership fact is presupposed",
            status=EpistemicStatus.PRESUPPOSED,  # → OPEN
        ),
        IntentionalCondition(
            name="data-subject-rights-addressee", dimension="relational",
            grounding=Grounding.span("data-subject-rights-addressee", "Art 15-21"),
            warrant="the policy enumerates the rights and the addressee for exercise",
            literal="data_subject_rights_and_addressee_stated",
            present=["data_subject_rights_and_addressee_stated"],
        ),
        IntentionalCondition(
            name="supervisory-authority-lead-identified", dimension="relational",
            grounding=Grounding.span("supervisory-authority-lead-identified", "Art 56"),
            warrant="the policy names the competent lead supervisory authority",
            literal="lead_supervisory_authority_named",
            present=["lead_supervisory_authority_named"],
        ),
        HonestGap(
            name="processor-actually-art28-compliant", dimension="relational",
            grounding=Grounding.gap(
                "processor-actually-art28-compliant",
                "that a GIVEN processor's contract and practice meet Art 28 is "
                "presupposed, not verified in the text"),
            warrant="per-processor verification is factual and presupposed",
            reason_text="processor-compliance verification not in panel scope",
        ),
        # ── intentional — lawful bases / purposes / norms (deontic half) ────────
        IntentionalCondition(
            name="lawful-basis-enumerated",
            grounding=Grounding.span("lawful-basis-enumerated", "Art 6(1)"),
            warrant="Art 6(1)(a)-(f): the policy lists the lawful bases it relies on",
            literal="lawful_bases_enumerated",
            present=["lawful_bases_enumerated"],
        ),
        IntentionalCondition(
            name="purpose-limitation-stated",
            grounding=Grounding.span("purpose-limitation-stated", "Art 5(1)(b)"),
            warrant="processing tied to specified, explicit, legitimate purposes",
            literal="purpose_limitation_stated",
            present=["purpose_limitation_stated"],
        ),
        IntentionalCondition(
            name="data-minimisation-principle",
            grounding=Grounding.span("data-minimisation-principle", "Art 5(1)(c)"),
            warrant="adequate, relevant, limited to what is necessary",
            literal="data_minimisation_stated",
            present=["data_minimisation_stated"],
        ),
        EpistemicPremise(
            name="lawful-basis-valid-for-this-processing",
            grounding=Grounding.gap(
                "lawful-basis-valid-for-this-processing",
                "that a VALID basis actually obtains for a concrete activity "
                "(consent freely given, or LI balancing passes) is presupposed"),
            warrant="the per-activity validity of a basis is presupposed",
            status=EpistemicStatus.PRESUPPOSED,  # → OPEN
        ),
        HonestGap(
            name="legitimate-interest-balancing-done",
            grounding=Grounding.gap(
                "legitimate-interest-balancing-done",
                "Art 6(1)(f) requires a balancing test whose outcome the policy "
                "asserts but does not perform in the text"),
            warrant="the balancing test is not constructed in the text",
            reason_text="legitimate-interest balancing construction not in panel scope",
        ),
        EpistemicPremise(
            name="accountability-demonstrable",
            grounding=Grounding.gap(
                "accountability-demonstrable",
                "Art 5(2): the DEMONSTRATION of compliance is a presupposed "
                "evidentiary state, not established by the policy asserting it"),
            warrant="the demonstrable-accountability state is presupposed",
            status=EpistemicStatus.PRESUPPOSED,  # → OPEN
        ),
        # ── nD — governance meta-norms ──────────────────────────────────────────
        IntentionalCondition(
            name="policy-review-cadence", dimension="nD",
            grounding=Grounding.span("policy-review-cadence", "policy §review"),
            warrant="the meta-norm stating the policy's own review cadence + owner",
            literal="review_cadence_and_owner_stated",
            present=["review_cadence_and_owner_stated"],
        ),
        IntentionalCondition(
            name="training-and-awareness-mandate", dimension="nD",
            grounding=Grounding.span("training-and-awareness-mandate", "Art 39(1)(b)"),
            warrant="the meta-norm binding staff to training and awareness",
            literal="training_and_awareness_mandate",
            present=["training_and_awareness_mandate"],
        ),
        IntentionalCondition(
            name="breach-register-maintained", dimension="nD",
            grounding=Grounding.span("breach-register-maintained", "Art 33(5)"),
            warrant="Art 33(5): the internal breach-documentation duty as meta-norm",
            literal="breach_register_maintained",
            present=["breach_register_maintained"],
        ),
        DeonticResolution(
            name="governance-override-when-laws-conflict", dimension="nD",
            grounding=Grounding.gap(
                "governance-override-when-laws-conflict",
                "how the policy resolves a conflict with another binding regime "
                "(e.g. a foreign disclosure order vs the GDPR erasure duty) is "
                "presupposed, no stated ordering → genuine collision"),
            warrant="two contradictory norms on the same act, no ordering → escalate",
            norms=[("erase_on_request", "obligatory", "GDPR Art 17"),
                   ("erase_on_request", "prohibited", "foreign_disclosure_order")],
            act="erase_on_request", pack="generic",  # collision → OPEN
        ),
    ),
    expected_subgraph=(
        NodeExpectation("structural", "policy-scope-personal-data-defined", Verdict.SATISFIED),
        NodeExpectation("structural", "policy-scope-processing-defined", Verdict.SATISFIED),
        NodeExpectation("structural", "special-category-data-carveout", Verdict.SATISFIED),
        NodeExpectation("structural", "records-of-processing-inventory", Verdict.SATISFIED),
        NodeExpectation("structural", "processing", Verdict.SATISFIED),
        NodeExpectation("structural", "controller", Verdict.SATISFIED),
        NodeExpectation("structural", "processor", Verdict.SATISFIED),
        NodeExpectation("structural", "special-category-lawful-condition-present", Verdict.OPEN),
        NodeExpectation("structural", "definition-closure-to-primitives", Verdict.OPEN),
        NodeExpectation("causal", "processing-causes-risk-to-rights", Verdict.OPEN),
        NodeExpectation("causal", "breach-likely-to-result-in-risk", Verdict.OPEN),
        NodeExpectation("causal", "dpia-high-risk-trigger", Verdict.OPEN),
        NodeExpectation("causal", "safeguards-mitigate-risk", Verdict.OPEN),
        NodeExpectation("temporal", "breach-notify-authority-72h", Verdict.SATISFIED),
        NodeExpectation("temporal", "breach-notify-data-subject-without-undue-delay", Verdict.SATISFIED),
        NodeExpectation("temporal", "dsar-response-one-month", Verdict.SATISFIED),
        NodeExpectation("temporal", "dsar-extension-two-months", Verdict.SATISFIED),
        NodeExpectation("temporal", "retention-period-per-category-stated", Verdict.SATISFIED),
        NodeExpectation("temporal", "retention-clock-trigger-event", Verdict.OPEN),
        NodeExpectation("temporal", "erasure-on-expiry-executed", Verdict.OPEN),
        NodeExpectation("temporal", "consent-withdrawal-effective-going-forward", Verdict.SATISFIED),
        NodeExpectation("relational", "controller-role-identified", Verdict.SATISFIED),
        NodeExpectation("relational", "dpo-appointed-and-contactable", Verdict.SATISFIED),
        NodeExpectation("relational", "processor-engaged-under-art28-contract", Verdict.SATISFIED),
        NodeExpectation("relational", "sub-processor-authorisation-chain", Verdict.SATISFIED),
        NodeExpectation("relational", "joint-controller-arrangement", Verdict.OPEN),
        NodeExpectation("relational", "data-subject-rights-addressee", Verdict.SATISFIED),
        NodeExpectation("relational", "supervisory-authority-lead-identified", Verdict.SATISFIED),
        NodeExpectation("relational", "processor-actually-art28-compliant", Verdict.OPEN),
        NodeExpectation("intentional", "lawful-basis-enumerated", Verdict.SATISFIED),
        NodeExpectation("intentional", "purpose-limitation-stated", Verdict.SATISFIED),
        NodeExpectation("intentional", "data-minimisation-principle", Verdict.SATISFIED),
        NodeExpectation("intentional", "lawful-basis-valid-for-this-processing", Verdict.OPEN),
        NodeExpectation("intentional", "legitimate-interest-balancing-done", Verdict.OPEN),
        NodeExpectation("intentional", "accountability-demonstrable", Verdict.OPEN),
        NodeExpectation("nD", "policy-review-cadence", Verdict.SATISFIED),
        NodeExpectation("nD", "training-and-awareness-mandate", Verdict.SATISFIED),
        NodeExpectation("nD", "breach-register-maintained", Verdict.SATISFIED),
        NodeExpectation("nD", "governance-override-when-laws-conflict", Verdict.OPEN),
    ),
    definition_closure={
        # honest: recursive definition-closure is NEEDS-BUILDING (§8.2). Only the
        # terms backed by a same-named SATISFIED structural stage resolve; every
        # open-textured or externally-conferred term stays OPEN (an honest pass),
        # never faked.
        "processing": "resolves_to_primitives",
        "controller": "resolves_to_primitives",
        "processor": "resolves_to_primitives",
        "personal-data": "OPEN",
        "special-category": "OPEN",
        "appropriate-safeguards": "OPEN",
        "consent": "OPEN",
        "adequate-level-of-protection": "OPEN",
    },
    understand_bar=UnderstandBar(
        who_what=("Governs the organisation acting as controller (and its engaged "
                  "processors / sub-processors) processing the personal data of "
                  "identified/identifiable natural persons. Roles, DPO contact, "
                  "and the data subject as rights-holder are all named "
                  "(structural + relational — grounded)."),
        conditions=("Processing is permitted only on an enumerated lawful basis "
                    "(Art 6(1)(a)-(f)), for a specified purpose, minimised to "
                    "necessity. OPEN: whether a VALID basis actually obtains for "
                    "any concrete activity — freely-given consent or a passing "
                    "legitimate-interest balancing — is presupposed per activity."),
        consequence=("Breach of the duties triggers the stated obligations (notify, "
                     "remediate, document) and exposes the organisation to Art 83 "
                     "supervisory sanction. OPEN: the causal risk-to-rights model "
                     "that scales the consequence (Art 33/34/35 'likely to result "
                     "in a risk') is presupposed, not modelled."),
        procedure=("Data-subject requests answered within one month (extendable two "
                   "months); breaches notified to the authority within 72 hours of "
                   "awareness and to data subjects without undue delay where "
                   "high-risk; processors engaged only under Art 28 contracts; a "
                   "breach register is maintained (temporal + relational — richly "
                   "grounded)."),
        purpose=("To protect the rights and freedoms of natural persons and to "
                 "demonstrate accountability (Art 5(2)) for lawful, fair, "
                 "transparent processing. OPEN: the demonstration of "
                 "accountability is an evidentiary state the policy asserts but "
                 "does not itself establish."),
        gaps=("OPEN: (1) a valid lawful basis per concrete activity; (2) the "
              "adequacy of any third-country transfer destination; (3) the "
              "'appropriateness' of the technical/organisational measures; (4) the "
              "entire causal risk-to-rights model (DPIA high-risk trigger, "
              "breach-risk likelihood); (5) that engaged processors are in fact "
              "Art 28-compliant; (6) recursive definition-closure of open-textured "
              "terms. Presupposed cells the layer must surface, never fill."),
    ),
    presupposed_probes=(
        PresupposedProbe("valid-lawful-basis-per-activity", Terminal.ESCALATE),
        PresupposedProbe("art32-measures-actually-adequate", Terminal.ESCALATE),
        PresupposedProbe("third-country-transfer-adequacy", Terminal.ESCALATE),
        PresupposedProbe("dpia-high-risk-judgement", Terminal.ESCALATE),
    ),
    probes=(
        Probe(
            kind="genuine_collision",
            note="the GDPR erasure duty vs a foreign disclosure / litigation-hold order",
            stages=(DeonticResolution(
                name="erasure_vs_disclosure_collision",
                grounding=Grounding.gap("erasure_vs_disclosure_collision",
                                        "no stated ordering between the erasure duty "
                                        "and a conflicting foreign order"),
                warrant="two contradictory norms on the same act, no ordering",
                norms=[("erase_on_request", "obligatory", "GDPR Art 17"),
                       ("erase_on_request", "prohibited", "foreign_disclosure_order")],
                act="erase_on_request", pack="generic"),),
        ),
        Probe(
            kind="presupposed_fact",
            note="a third-country transfer destination's adequacy is presupposed",
            stages=(EpistemicPremise(
                name="transfer_adequacy_presupposed",
                grounding=Grounding.gap("transfer_adequacy_presupposed",
                                        "adequacy is an external Commission act, "
                                        "presupposed for a given destination"),
                warrant="a presupposed adequacy fact cannot be rested on",
                status=EpistemicStatus.PRESUPPOSED),),
        ),
        Probe(
            kind="unsettled_reading",
            note="whether a legitimate-interest balancing passes on the facts",
            stages=(EpistemicPremise(
                name="li_balancing_unsettled",
                grounding=Grounding.gap("li_balancing_unsettled",
                                        "the balancing outcome is contested on the facts"),
                warrant="a contested balancing is a human's call, not the engine's",
                status=EpistemicStatus.CONTESTED),),
        ),
    ),
)
