# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Contract case — an employment clause waiving the statutory minimum notice.

An employment contract clause purports to shorten the employer's notice period
below the statutory minimum of §622 BGB to the employee's disadvantage. §622
Abs. 6 BGB forbids agreeing a longer notice for the employee than the employer;
the graduated minimum periods are mandatory and a clause undercutting them to the
employee's detriment is void (§134 BGB). The elements fire as closed-world /
structural conditions (all SATISFIED), and the operative deontic consequence —
the party is *obligated to be able to disregard* the void waiver (the statutory
period applies in its place) — is resolved by the real deontic solver: the
mandatory statute (lex superior, rank 5) defeats the drafter's waiver (rank 1) →
obligatory → SATISFIED. All SATISFIED → **DETERMINATE (waiver void)**. The
terminal is COMPUTED from the stages, never asserted.

This case is a secondary contract-bucket **signed-replay (H4)** source: its
:class:`DeonticResolution` exposes an intact trace the grader re-derives → PASS.

Probe (must ESCALATE):

  * ``genuine_collision`` — the same clause defended under freedom of contract
    (§105 GewO) versus the mandatory §622 Abs. 6 floor, two contradictory norms
    with no ordering → the deontic solver returns ``status=open`` → OPEN.
"""
from __future__ import annotations

from ... import (
    CaseSpec, DeonticResolution, Grounding, IntentionalCondition, Probe,
    StructuralCondition, Terminal, is_a,
)


CASE = CaseSpec(
    id="contract.employment.para622.notice_waiver",
    title="Employment clause waiving the §622 BGB minimum notice is void",
    case_kind="contract",
    source_text=(
        "§622 Abs. 1/2 BGB: the employment relationship may be terminated only "
        "on the statutory graduated notice periods. §622 Abs. 6 BGB: no longer "
        "notice period may be agreed for the employee than for the employer. "
        "§134 BGB: a legal transaction contravening a statutory prohibition is "
        "void. Clause: 'The employee waives the statutory minimum notice period "
        "and accepts termination on three days' notice.'"
    ),
    question=("Is the clause waiving the §622 BGB minimum notice period void?"),
    expected_terminal=Terminal.DETERMINATE,   # non-waivable right → waiver void
    stages=(
        IntentionalCondition(
            name="waives_statutory_notice",
            grounding=Grounding.span("waives_statutory_notice",
                                     "clause: waives the minimum notice"),
            warrant="the clause undercuts the statutory minimum notice to the "
                    "employee's disadvantage",
            literal="waives_minimum_notice_to_employee_disadvantage",
            present=["waives_minimum_notice_to_employee_disadvantage",
                     "is_employment_contract_term"],
        ),
        IntentionalCondition(
            name="is_employment_term",
            grounding=Grounding.span("is_employment_term", "§622 BGB"),
            warrant="§622: the term is a notice provision in an employment "
                    "relationship",
            literal="is_employment_contract_term",
            present=["waives_minimum_notice_to_employee_disadvantage",
                     "is_employment_contract_term"],
        ),
        StructuralCondition(
            name="notice_right_non_waivable",
            grounding=Grounding.span("notice_right_non_waivable",
                                     "§622 Abs. 6 i.V.m. §134 BGB"),
            warrant="§622(6)/§134: the minimum-notice right is-a non-waivable "
                    "mandatory statutory right",
            subject="minimum_notice_right",
            object="non_waivable_statutory_right",
            edges=[is_a("minimum_notice_right", "mandatory_protective_right"),
                   is_a("mandatory_protective_right",
                        "non_waivable_statutory_right")],
        ),
        DeonticResolution(
            name="disregard_void_waiver",
            grounding=Grounding.span("disregard_void_waiver",
                                     "§134 i.V.m. §622 BGB"),
            warrant="§134+§622 (lex superior, rank 5) defeats the waiver clause "
                    "(rank 1): the statutory period applies in its place",
            dimension="intentional",
            norms=[("disregard_void_waiver", "obligatory", "§622/§134 BGB", 0, 5),
                   ("disregard_void_waiver", "prohibited",
                    "the waiver clause purports to bind", 0, 1)],
            act="disregard_void_waiver", pack="lex",   # statute wins → obligatory
        ),
    ),
    probes=(
        Probe(
            kind="genuine_collision",
            note="waiver defended under freedom of contract vs mandatory §622(6), "
                 "no ordering",
            stages=(DeonticResolution(
                name="collision",
                grounding=Grounding.span("collision", "§105 GewO vs §622 Abs. 6 BGB"),
                warrant="two contradictory norms on the same clause, no ordering",
                norms=[("enforce_waiver", "permitted", "§105 GewO freedom of contract"),
                       ("enforce_waiver", "prohibited", "§622 Abs. 6 BGB")],
                act="enforce_waiver", pack="generic"),),
        ),
    ),
)
