# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Statute case — §309 BGB standard-terms blacklist (a per-se void clause).

§309 BGB is the *Klauselverbote ohne Wertungsmöglichkeit* — a blacklist of
standard-terms clauses void with no room for evaluation. A pre-formulated clause
that shifts the burden of proof to the customer's disadvantage falls under
§309 Nr. 12; a clause on the blacklist is void per se. The elements fire as
closed-world / structural conditions (all SATISFIED), and the operative deontic
consequence — the customer is *obligated to be able to disregard* the void
clause (§306: the contract stands without it) — is resolved by the real deontic
solver: the statutory norm (lex superior, rank 5) defeats the drafter's clause
(rank 1) → obligatory → SATISFIED. All SATISFIED → **DETERMINATE (void)**.

This case is also the panel's **signed-replay (H4)** source in the statute
bucket: its :class:`DeonticResolution` exposes an intact derivation trace that
the grader re-derives and scores PASS.

Probe (must ESCALATE):

  * ``genuine_collision`` — a clause hitting two rules with no ordering: it both
    excludes liability for a guaranteed characteristic (§309 Nr. 7/8 territory)
    AND is defended as an individually-agreed term (§305 freedom of contract),
    with no priority between the two readings → the deontic solver returns
    ``status=open`` → OPEN.
"""
from __future__ import annotations

from ... import (
    CaseSpec, DeonticResolution, Grounding, IntentionalCondition, Probe,
    StructuralCondition, Terminal, is_a,
)


CASE = CaseSpec(
    id="statute.bgb.para309.clause_blacklist",
    title="§309 BGB blacklist — burden-of-proof-shifting clause is void per se",
    case_kind="statute",
    source_text=(
        "§309 Nr. 12 BGB: In allgemeinen Geschäftsbedingungen ist unwirksam "
        "eine Bestimmung, durch die der Verwender die Beweislast zum Nachteil "
        "des anderen Vertragsteils ändert. §306 Abs. 1/2 BGB: bei Unwirksamkeit "
        "bleibt der Vertrag im Übrigen wirksam; an die Stelle der unwirksamen "
        "Klausel treten die gesetzlichen Vorschriften."
    ),
    question=("Is the burden-of-proof-shifting standard term void under "
              "§309 Nr. 12 BGB?"),
    expected_terminal=Terminal.DETERMINATE,   # blacklisted → void per se
    stages=(
        IntentionalCondition(
            name="is_standard_term",
            grounding=Grounding.span("is_standard_term", "§305 Abs. 1 BGB"),
            warrant="§305(1): a pre-formulated, non-negotiated term is an AGB",
            literal="is_pre_formulated_standard_term",
            present=["is_pre_formulated_standard_term",
                     "shifts_burden_of_proof_to_customer"],
        ),
        IntentionalCondition(
            name="shifts_burden_of_proof",
            grounding=Grounding.span("shifts_burden_of_proof", "§309 Nr. 12 BGB"),
            warrant="§309 Nr. 12: the clause shifts the burden of proof to the "
                    "customer's disadvantage",
            literal="shifts_burden_of_proof_to_customer",
            present=["is_pre_formulated_standard_term",
                     "shifts_burden_of_proof_to_customer"],
        ),
        StructuralCondition(
            name="on_the_blacklist",
            grounding=Grounding.span("on_the_blacklist", "§309 Nr. 12 BGB"),
            warrant="§309: the clause type is on the no-evaluation blacklist",
            subject="burden_shifting_clause", object="section_309_blacklist",
            edges=[is_a("burden_shifting_clause", "burden_of_proof_clause"),
                   is_a("burden_of_proof_clause", "section_309_blacklist")],
        ),
        DeonticResolution(
            name="disregard_void_clause",
            grounding=Grounding.span("disregard_void_clause", "§306 i.V.m. §309 BGB"),
            warrant="§306+§309 (lex superior, rank 5) defeats the drafter's "
                    "clause (rank 1): the void term does not bind",
            dimension="intentional",
            norms=[("disregard_void_clause", "obligatory", "§309/§306 BGB", 0, 5),
                   ("disregard_void_clause", "prohibited",
                    "the AGB clause purports to bind", 0, 1)],
            act="disregard_void_clause", pack="lex",   # statute wins → obligatory
        ),
    ),
    probes=(
        Probe(
            kind="genuine_collision",
            note="void-per-§309 vs defended-as-individually-agreed, no ordering",
            stages=(DeonticResolution(
                name="collision",
                grounding=Grounding.span("collision", "§309 vs §305 BGB"),
                warrant="two contradictory readings of the same clause, no ordering",
                norms=[("enforce_clause", "prohibited", "§309 Nr. 12 BGB"),
                       ("enforce_clause", "permitted", "§305 freedom of contract")],
                act="enforce_clause", pack="generic"),),
        ),
    ),
)
