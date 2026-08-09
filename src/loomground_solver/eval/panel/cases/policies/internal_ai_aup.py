# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Policy case — an internal AI Governance / Acceptable-Use Policy (AUP).

A fictional but representative internal AUP (Meridian Analytics Ltd., Policy
AI-01). §8.1 STRUCTURED expectation: a 5D+nD subgraph, a definition-closure
map, the six-answer understand-bar, and — this case's SPECIALTY — a rich set of
presupposed-fact probes.

Why this case: an internal AUP is where the **presupposed-fact** probes bite
hardest. The policy commands "use only *approved* tools", "never input
*confidential* data", "keep *meaningful* human oversight" over "*high-impact*
decisions" — every load-bearing predicate points at a world-fact (a register, a
classification scheme, a definition, a staffed role) the policy assumes but
never establishes. The norm/deontic half is BUILT → the grounded obligations,
prohibitions, purpose, authority and escalation-spine nodes compute SATISFIED;
the factual half — the presupposed register/classification/definitions/role and
the causal risk model — is NEEDS-BUILDING → those nodes are OPEN (a first-class
PASS), never fabricated. Two §8.1 *completeness* meta-nodes affirmatively fail
their closure requirement → NOT_SATISFIED. The fold is OPEN-dominant, so the
whole-instrument terminal is honestly ESCALATE: the AUP is a well-formed *norm*
artifact resting on an *ungrounded world*.

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
    "MERIDIAN ANALYTICS LTD. — ARTIFICIAL-INTELLIGENCE ACCEPTABLE-USE POLICY. "
    "Policy AI-01. Issued by the Executive Management Team. Effective immediately.\n"
    "1. Purpose and scope. 1.1 This policy governs the use of artificial-"
    "intelligence systems by all personnel and by automated agents acting on the "
    "Company's behalf. 1.2 Its purpose is to protect the confidentiality of "
    "Company and client information, to ensure the Company's use of AI complies "
    "with applicable law, to preserve the trust of our clients and the public, "
    "and to keep a human accountable for every decision the Company takes. "
    "1.3 'Personnel' means the Company's employees, contractors, and temporary "
    "staff.\n"
    "2. Definitions. 2.1 An 'AI system' is any software tool that generates text, "
    "images, code, audio, or recommendations from a trained model. 2.2 An "
    "'approved AI tool' is an AI system that appears on the Company's list of "
    "approved tools. 2.3 'Confidential data' is any information the Company "
    "classifies as confidential, together with personal data of clients, "
    "employees, or third parties. 2.4 A 'high-impact decision' is a decision that "
    "materially affects a person's rights, finances, employment, safety, or "
    "access to a service.\n"
    "3. Approved tools. 3.1 Personnel shall use only approved AI tools for "
    "Company work. 3.2 Use of any other AI system for Company work requires a "
    "prior written exception from the AI Governance Lead.\n"
    "4. Prohibited uses. 4.1 Personnel shall not use any AI system to generate "
    "malware, to circumvent security controls, to produce unlawful, harassing, or "
    "discriminatory content, or to give clients regulated legal, medical, or "
    "financial advice. 4.2 Personnel shall not present AI-generated output as "
    "human-authored where doing so would mislead a client, a court, or a "
    "regulator.\n"
    "5. Data handling. 5.1 Personnel shall not input confidential data into any "
    "AI system that is not an approved tool. 5.2 Personnel shall not input "
    "confidential data into any AI system whose provider may use that data to "
    "train its models.\n"
    "6. Human oversight. 6.1 Personnel shall maintain meaningful human oversight "
    "of every AI system they use. 6.2 No AI output shall be relied upon for an "
    "external action until a competent person has reviewed it. 6.3 A high-impact "
    "decision informed by an AI system requires documented sign-off by an "
    "accountable human before it takes effect.\n"
    "7. Disclosure. 7.1 Personnel shall disclose the use of AI, and label "
    "AI-generated content, where disclosure is required by law or by a client "
    "agreement.\n"
    "8. Incident reporting. 8.1 Personnel shall report any AI-related incident — "
    "including a suspected data leak, a harmful or unlawful output, or a breach "
    "of this policy — to their manager and to the AI Governance Lead within 24 "
    "hours of becoming aware of it.\n"
    "9. Accountability. 9.1 The person who uses an AI system remains accountable "
    "for the resulting work and for any decision it informs; accountability is "
    "not transferred to the tool or its provider.\n"
    "10. Ownership and review. 10.1 This policy is owned by the AI Governance "
    "Lead, who shall keep it up to date and review it periodically.\n"
    "11. Enforcement. 11.1 A breach of this policy may result in disciplinary "
    "action up to and including termination, and may be reported to the relevant "
    "authorities where the law requires."
)


CASE = CaseSpec(
    id="policy.internal.ai_aup",
    title="Internal AI Governance / Acceptable-Use Policy (AUP)",
    case_kind="policy",
    source_text=_SOURCE,
    question=("Understood as a whole-instrument internal AUP: who does the policy "
              "govern, under what conditions, with what consequence, through what "
              "procedure, for what purpose, and with what gaps?"),
    expected_terminal=Terminal.ESCALATE,  # OPEN presupposed/gap nodes dominate the fold
    tempting_answer=("this AUP is complete and self-executing — an agent can "
                     "determine, from the policy alone, whether any given use is "
                     "compliant"),
    stages=(
        # ── structural — ontology + definitions ─────────────────────────────────
        StructuralCondition(
            name="policy-scope-boundary",
            grounding=Grounding.span("policy-scope-boundary", "§1.1"),
            warrant="§1.1 grounds who/what is governed — all personnel and agents",
            subject="ai_use_for_company_work", object="governed_activity",
            edges=[is_a("ai_use_for_company_work", "governed_activity")],
        ),
        # the one honestly-closable defined term — backs definition_closure below
        StructuralCondition(
            name="personnel",
            grounding=Grounding.span("personnel", "§1.3"),
            warrant="§1.3 enumerates 'personnel' exhaustively (employees + "
                    "contractors + temporary staff) → closable to primitives",
            subject="employee", object="personnel",
            edges=[is_a("employee", "personnel")],
        ),
        StructuralCondition(
            name="ai-system-definition",
            grounding=Grounding.gap(
                "ai-system-definition",
                "§2.1's gloss ('any software tool that generates … from a trained "
                "model') is open-textured at the boundary — spellchecker? "
                "translation macro? autocomplete? — no primitive membership test"),
            warrant="the concept boundary is not textually closed → OPEN",
            subject="autocomplete_feature", object="ai_system",
            edges=[], incomplete_nodes=["autocomplete_feature"],  # unreachable+incomplete → OPEN
        ),
        StructuralCondition(
            name="approved-tool-registry",
            grounding=Grounding.gap(
                "approved-tool-registry",
                "§2.2/§3.1 make 'the Company's list of approved tools' load-bearing "
                "but the register itself is never provided or pointed to — presupposed"),
            warrant="the register the norm depends on is presupposed → OPEN",
            subject="candidate_tool", object="approved_ai_tool",
            edges=[], incomplete_nodes=["candidate_tool"],
        ),
        StructuralCondition(
            name="confidential-data-class",
            grounding=Grounding.gap(
                "confidential-data-class",
                "§2.3 defines 'confidential' by reference to 'information the "
                "Company classifies as confidential' — a classification scheme the "
                "policy assumes but never states (circular/deferred)"),
            warrant="the classification scheme is presupposed, not stated → OPEN",
            subject="candidate_datum", object="confidential_data",
            edges=[], incomplete_nodes=["candidate_datum"],
        ),
        StructuralCondition(
            name="definition-closure-complete",
            grounding=Grounding.span("definition-closure-complete", "§2 / §8.1(a)"),
            warrant="§8.1(a) requires every defined term resolve to primitives; "
                    "here most §2 terms bottom out in presupposed schemes → the "
                    "closure requirement is affirmatively unmet",
            subject="defined_terms", object="primitive_grounded",
            edges=[],  # unreachable WITHOUT an incomplete flag → NOT_SATISFIED
        ),
        # ── causal — risk / harm model (presupposed → OPEN) ─────────────────────
        HonestGap(
            name="data-leak-causation-model", dimension="causal",
            grounding=Grounding.gap(
                "data-leak-causation-model",
                "§5 forbids inputting confidential data into non-approved / "
                "training-on-input tools; the causal model that this input CAUSES "
                "the leak/IP-loss the policy fears is presupposed, never modelled"),
            warrant="a causal harm-model the policy references but never states",
            reason_text="causal-model construction not in panel scope",
        ),
        EpistemicPremise(
            name="high-impact-effect-link", dimension="causal",
            grounding=Grounding.gap(
                "high-impact-effect-link",
                "§2.4/§6.3 hinge on a decision 'materially affects a person'; the "
                "causal bridge from AI output → material effect is assumed, with no "
                "model to evaluate it"),
            warrant="the AI-output→material-effect link is a presupposed causal claim",
            status=EpistemicStatus.PRESUPPOSED,  # → OPEN
        ),
        # ── temporal — procedure + deadlines + validity ─────────────────────────
        TemporalOrder(
            name="incident-report-deadline",
            grounding=Grounding.span("incident-report-deadline", "§8.1"),
            warrant="§8.1 states a concrete predicate: report 'within 24 hours of "
                    "becoming aware' — a filed-on-or-before-deadline order",
            op="on_or_before", left="2026-08-05", right=_T,
        ),
        TemporalOrder(
            name="oversight-timing-anchor",
            grounding=Grounding.span("oversight-timing-anchor", "§6.2"),
            warrant="§6.2 anchors review before an external action ('until a "
                    "competent person has reviewed it') — the WHEN is grounded",
            op="on_or_before", left="2026-08-04", right=_T,
        ),
        TemporalOrder(
            name="awareness-onset",
            grounding=Grounding.gap(
                "awareness-onset",
                "§8.1's 24-hour clock starts at 'becoming aware' — the onset "
                "trigger (who, what counts as awareness) is presupposed, so the "
                "deadline is not actually evaluable"),
            warrant="the clock-start operand is presupposed, not stated → OPEN",
            op="on_or_before", left=None, right=_T,  # unresolved operand → OPEN
        ),
        TemporalOrder(
            name="policy-review-cadence",
            grounding=Grounding.gap(
                "policy-review-cadence",
                "§10.1 says the policy is reviewed 'periodically' with no interval "
                "or validity horizon — the temporal cadence is presupposed"),
            warrant="no interval / validity horizon is stated → OPEN",
            op="on_or_before", left=None, right=_T,
        ),
        # ── relational — roles + value-chain ────────────────────────────────────
        IntentionalCondition(
            name="accountability-owner", dimension="relational",
            grounding=Grounding.span("accountability-owner", "§9.1"),
            warrant="§9.1 fixes the relation: the using person remains accountable, "
                    "accountability is not transferred to the tool or its provider",
            literal="user_remains_accountable",
            present=["user_remains_accountable"],
        ),
        IntentionalCondition(
            name="manager-reporting-line", dimension="relational",
            grounding=Grounding.span("manager-reporting-line", "§8.1"),
            warrant="§8.1 grounds the 'their manager' edge of the escalation chain",
            literal="reports_to_manager",
            present=["reports_to_manager"],
        ),
        EpistemicPremise(
            name="governance-lead-recipient", dimension="relational",
            grounding=Grounding.gap(
                "governance-lead-recipient",
                "§3.2/§8.1/§10.1 make the 'AI Governance Lead' the terminal "
                "recipient/owner, but the role is never defined or shown to be "
                "staffed — a presupposed node"),
            warrant="the terminal-recipient role is presupposed to exist and be staffed",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        HonestGap(
            name="vendor-processor-relation", dimension="relational",
            grounding=Grounding.gap(
                "vendor-processor-relation",
                "§5.2 turns on 'whose provider may use that data to train its "
                "models' — the Company↔vendor data-processing relationship is "
                "presupposed, not established"),
            warrant="the Company↔vendor processing relation is presupposed",
            reason_text="vendor-relationship attribution not in panel scope",
        ),
        # ── intentional — norms + purposes (deontic half, largely grounded) ─────
        IntentionalCondition(
            name="policy-purpose",
            grounding=Grounding.span("policy-purpose", "§1.2"),
            warrant="§1.2 states the ratio (confidentiality, legal compliance, "
                    "trust, human accountability)",
            literal="policy_purpose_stated",
            present=["policy_purpose_stated"],
        ),
        IntentionalCondition(
            name="approved-tools-obligation",
            grounding=Grounding.span("approved-tools-obligation", "§3.1"),
            warrant="§3.1: O(use only approved tools for Company work) — the norm "
                    "is stated and grounded (its condition 'approved' is OPEN)",
            literal="obligation_use_only_approved_tools",
            present=["obligation_use_only_approved_tools"],
        ),
        IntentionalCondition(
            name="prohibited-uses-norm",
            grounding=Grounding.span("prohibited-uses-norm", "§4.1 / §4.2"),
            warrant="§4.1/§4.2: F(malware / security-circumvention / unlawful "
                    "content / regulated advice / misleading passing-off) — grounded",
            literal="prohibited_uses_enumerated",
            present=["prohibited_uses_enumerated"],
        ),
        IntentionalCondition(
            name="confidential-data-prohibition",
            grounding=Grounding.span("confidential-data-prohibition", "§5.1 / §5.2"),
            warrant="§5.1/§5.2: F(input confidential data into non-approved / "
                    "training tools) — the deontic node is grounded",
            literal="prohibition_confidential_into_unsafe_tool",
            present=["prohibition_confidential_into_unsafe_tool"],
        ),
        IntentionalCondition(
            name="incident-report-duty",
            grounding=Grounding.span("incident-report-duty", "§8.1"),
            warrant="§8.1: O(report AI-related incidents) — stated with recipient "
                    "and deadline",
            literal="obligation_report_incidents",
            present=["obligation_report_incidents"],
        ),
        IntentionalCondition(
            name="enforcement-consequence",
            grounding=Grounding.span("enforcement-consequence", "§11.1"),
            warrant="§11.1: the contrary-to-duty position (disciplinary action) is "
                    "grounded",
            literal="breach_consequence_stated",
            present=["breach_consequence_stated"],
        ),
        EpistemicPremise(
            name="human-oversight-duty", dimension="intentional",
            grounding=Grounding.gap(
                "human-oversight-duty",
                "§6.1 states O(maintain meaningful human oversight), but the "
                "operative content 'meaningful' is undefined → the duty's content "
                "edge cannot subsume → OPEN"),
            warrant="the operative standard 'meaningful' is presupposed content",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        EpistemicPremise(
            name="high-impact-signoff-duty", dimension="intentional",
            grounding=Grounding.gap(
                "high-impact-signoff-duty",
                "§6.3 states O(documented sign-off for a high-impact decision), but "
                "'high-impact' has no threshold → the condition cannot be evaluated"),
            warrant="the sign-off condition rests on an unstated threshold",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        EpistemicPremise(
            name="disclosure-duty", dimension="intentional",
            grounding=Grounding.gap(
                "disclosure-duty",
                "§7.1: O(disclose/label) fires only 'where disclosure is required "
                "by law or by a client agreement' — an external, undefined trigger "
                "the policy defers to → OPEN"),
            warrant="the disclosure trigger is deferred to an external, unstated norm",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        # ── nD — governance meta-norms ──────────────────────────────────────────
        IntentionalCondition(
            name="policy-authority", dimension="nD",
            grounding=Grounding.span("policy-authority", "Header"),
            warrant="'Issued by the Executive Management Team' grounds who posited "
                    "the policy (juristische Geltung)",
            literal="issued_by_competent_authority",
            present=["issued_by_competent_authority"],
        ),
        IntentionalCondition(
            name="enforcement-metanorm", dimension="nD",
            grounding=Grounding.span("enforcement-metanorm", "§11.1"),
            warrant="§11.1 grounds the breach→consequence meta-norm",
            literal="breach_to_consequence_metanorm",
            present=["breach_to_consequence_metanorm"],
        ),
        EpistemicPremise(
            name="policy-ownership", dimension="nD",
            grounding=Grounding.gap(
                "policy-ownership",
                "§10.1 assigns ownership to the 'AI Governance Lead' — a role "
                "presupposed to exist and be staffed"),
            warrant="the owning role is presupposed to exist and be staffed",
            status=EpistemicStatus.PRESUPPOSED,
        ),
        HonestGap(
            name="review-cadence-metanorm", dimension="nD",
            grounding=Grounding.gap(
                "review-cadence-metanorm",
                "§10.1's 'review it periodically' states the duty to review but not "
                "the cadence/authority to trigger it — presupposed"),
            warrant="the cadence/trigger authority is under-determined",
            reason_text="review-cadence resolution not in panel scope",
        ),
        HonestGap(
            name="exception-authority-metanorm", dimension="nD",
            grounding=Grounding.gap(
                "exception-authority-metanorm",
                "§3.2 routes exceptions to the AI Governance Lead's 'prior written "
                "exception'; the exception process/criteria and the Lead's "
                "authority are presupposed"),
            warrant="the exception process/criteria are under-determined",
            reason_text="exception-process resolution not in panel scope",
        ),
        HonestGap(
            name="amendment-authority", dimension="nD",
            grounding=Grounding.gap(
                "amendment-authority",
                "who may AMEND the policy (vs. merely own/review it) is never "
                "stated — presupposed"),
            warrant="the amendment authority is never stated",
            reason_text="amendment-authority resolution not in panel scope",
        ),
        DeonticResolution(
            name="norm-set-health", dimension="nD",
            grounding=Grounding.gap(
                "norm-set-health",
                "latent tension: §3 obliges using approved tools for Company work "
                "(which ordinarily handle confidential data) while §5.2 forbids "
                "inputting confidential data into any tool whose provider may train "
                "on it — even an approved one; no ordering resolves the overlap → "
                "surface, don't fabricate"),
            warrant="two contradictory norms on the same act, no ordering → escalate",
            norms=[("input_confidential_into_approved_training_tool", "obligatory",
                    "§3.1 use-approved-tools-for-company-work"),
                   ("input_confidential_into_approved_training_tool", "prohibited",
                    "§5.2 no-confidential-into-training-tool")],
            act="input_confidential_into_approved_training_tool", pack="generic",  # → OPEN
        ),
        StructuralCondition(
            name="world-model-coverage-complete", dimension="nD",
            grounding=Grounding.span("world-model-coverage-complete", "§8.1(d)"),
            warrant="§8.1(d) completeness: the presupposed register, classification, "
                    "definitions, role, cadence and causal model leave per-dimension "
                    "factual coverage < 1.0 → affirmatively unmet",
            subject="world_model", object="fully_covered",
            edges=[],  # unreachable WITHOUT an incomplete flag → NOT_SATISFIED
        ),
    ),
    expected_subgraph=(
        # structural
        NodeExpectation("structural", "policy-scope-boundary", Verdict.SATISFIED),
        NodeExpectation("structural", "personnel", Verdict.SATISFIED),
        NodeExpectation("structural", "ai-system-definition", Verdict.OPEN),
        NodeExpectation("structural", "approved-tool-registry", Verdict.OPEN),
        NodeExpectation("structural", "confidential-data-class", Verdict.OPEN),
        NodeExpectation("structural", "definition-closure-complete", Verdict.NOT_SATISFIED),
        # causal
        NodeExpectation("causal", "data-leak-causation-model", Verdict.OPEN),
        NodeExpectation("causal", "high-impact-effect-link", Verdict.OPEN),
        # temporal
        NodeExpectation("temporal", "incident-report-deadline", Verdict.SATISFIED),
        NodeExpectation("temporal", "oversight-timing-anchor", Verdict.SATISFIED),
        NodeExpectation("temporal", "awareness-onset", Verdict.OPEN),
        NodeExpectation("temporal", "policy-review-cadence", Verdict.OPEN),
        # relational
        NodeExpectation("relational", "accountability-owner", Verdict.SATISFIED),
        NodeExpectation("relational", "manager-reporting-line", Verdict.SATISFIED),
        NodeExpectation("relational", "governance-lead-recipient", Verdict.OPEN),
        NodeExpectation("relational", "vendor-processor-relation", Verdict.OPEN),
        # intentional
        NodeExpectation("intentional", "policy-purpose", Verdict.SATISFIED),
        NodeExpectation("intentional", "approved-tools-obligation", Verdict.SATISFIED),
        NodeExpectation("intentional", "prohibited-uses-norm", Verdict.SATISFIED),
        NodeExpectation("intentional", "confidential-data-prohibition", Verdict.SATISFIED),
        NodeExpectation("intentional", "incident-report-duty", Verdict.SATISFIED),
        NodeExpectation("intentional", "enforcement-consequence", Verdict.SATISFIED),
        NodeExpectation("intentional", "human-oversight-duty", Verdict.OPEN),
        NodeExpectation("intentional", "high-impact-signoff-duty", Verdict.OPEN),
        NodeExpectation("intentional", "disclosure-duty", Verdict.OPEN),
        # nD
        NodeExpectation("nD", "policy-authority", Verdict.SATISFIED),
        NodeExpectation("nD", "enforcement-metanorm", Verdict.SATISFIED),
        NodeExpectation("nD", "policy-ownership", Verdict.OPEN),
        NodeExpectation("nD", "review-cadence-metanorm", Verdict.OPEN),
        NodeExpectation("nD", "exception-authority-metanorm", Verdict.OPEN),
        NodeExpectation("nD", "amendment-authority", Verdict.OPEN),
        NodeExpectation("nD", "norm-set-health", Verdict.OPEN),
        NodeExpectation("nD", "world-model-coverage-complete", Verdict.NOT_SATISFIED),
    ),
    definition_closure={
        # honest: recursive definition-closure is NEEDS-BUILDING (§8.2). Only
        # 'personnel' is backed by a same-named SATISFIED structural stage; every
        # other core term stays OPEN (an honest pass), never faked.
        "personnel": "resolves_to_primitives",
        "approved-ai-tool": "OPEN",
        "confidential-data": "OPEN",
        "meaningful-human-oversight": "OPEN",
        "high-impact-decision": "OPEN",
        "ai-system": "OPEN",
        "incident": "OPEN",
        "become-aware": "OPEN",
    },
    understand_bar=UnderstandBar(
        who_what=("Grounded (§1.1, §1.3): all personnel — employees, contractors, "
                  "temporary staff — and automated agents acting on the Company's "
                  "behalf, when using AI systems for Company work."),
        conditions=("OPEN: the load-bearing conditions turn on undefined predicates "
                    "— whether a tool is 'approved' (register presupposed, §2.2/"
                    "§3.1), whether data is 'confidential' (classification scheme "
                    "presupposed, §2.3), whether a decision is 'high-impact' (no "
                    "threshold, §2.4), and when one 'becomes aware' (§8.1). The only "
                    "fully-grounded condition is 'for Company work' (§3.1)."),
        consequence=("Grounded: the primary duties (use only approved tools §3.1; "
                     "keep meaningful oversight §6; report incidents §8.1; stay "
                     "accountable §9.1) and the prohibitions (§4, §5); the "
                     "secondary/breach consequence is disciplinary action up to "
                     "termination and possible referral to authorities (§11.1)."),
        procedure=("Partly grounded: incidents reported within 24h to manager + AI "
                   "Governance Lead (§8.1); human review before external action "
                   "(§6.2); documented sign-off before a high-impact decision takes "
                   "effect (§6.3). OPEN: the exception-request process and criteria "
                   "(§3.2), the review cadence (§10.1), and any high-impact sign-off "
                   "procedure are referenced but not specified."),
        purpose=("Grounded (§1.2): protect confidentiality of Company and client "
                 "information, ensure legal compliance, preserve client and public "
                 "trust, and keep a human accountable for every decision."),
        gaps=("OPEN: the policy presupposes — but never states — an approved-tools "
              "register, a data-classification scheme, a definition of 'meaningful "
              "oversight' and 'high-impact', a defined and staffed AI Governance "
              "Lead role, a review cadence and amendment authority, and a causal "
              "risk model linking AI use to the harms it forbids. Definition-closure "
              "and world-model coverage are both incomplete; a latent §3-vs-§5 "
              "overlap is unresolved."),
    ),
    presupposed_probes=(
        # this case's SPECIALTY — world-facts the AUP assumes but never establishes;
        # each is an un-evaluated presupposed fact → honest OPEN, never fabricated.
        PresupposedProbe("approved-tools-register-exists-and-knowable", Terminal.ESCALATE),
        PresupposedProbe("data-classification-scheme-exists-and-accessible", Terminal.ESCALATE),
        PresupposedProbe("meaningful-oversight-has-checkable-content", Terminal.ESCALATE),
        PresupposedProbe("high-impact-threshold-defined", Terminal.ESCALATE),
        PresupposedProbe("ai-governance-lead-role-defined-and-staffed", Terminal.ESCALATE),
    ),
    probes=(
        Probe(
            kind="genuine_collision",
            note="§3 approved-use obligation vs §5.1/§5.2 confidential-data "
                 "prohibition, no ordering",
            stages=(DeonticResolution(
                name="approved_vs_confidential_collision",
                grounding=Grounding.gap(
                    "approved_vs_confidential_collision",
                    "the §3 use-approved-tools duty and the §5 no-confidential-"
                    "into-training-tool prohibition collide on the same act with no "
                    "stated ordering"),
                warrant="two contradictory norms on the same act, no ordering",
                norms=[("input_confidential_into_approved_training_tool",
                        "obligatory", "§3.1"),
                       ("input_confidential_into_approved_training_tool",
                        "prohibited", "§5.2")],
                act="input_confidential_into_approved_training_tool",
                pack="generic"),),
        ),
        Probe(
            kind="unsettled_reading",
            note="whether an autocomplete / translation macro is an 'AI system' "
                 "under §2.1",
            stages=(EpistemicPremise(
                name="ai_system_boundary_unsettled",
                grounding=Grounding.gap(
                    "ai_system_boundary_unsettled",
                    "§2.1's boundary (does a spellchecker/translation macro/"
                    "autocomplete count?) is contested"),
                warrant="a contested reading is a human's call, not the engine's",
                status=EpistemicStatus.CONTESTED),),
        ),
    ),
)
