# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Cross-dimensional subsumption: routing a norm condition to its dimension
evaluator, and aggregating an antecedent under strict-AND-with-escalation.

Deterministic throughout — fixed facts + a condition → a fixed verdict — plus
the OPEN/escalate branches, which are first-class correct verdicts: an
incomplete (presupposed) causal link, a contested relation chain, an unresolved
date, and an undeterminable dimension all resolve to OPEN, never to a guess and
never to a fabricated satisfaction.
"""
from __future__ import annotations

from loomground_solver.cross_subsumption import (
    Condition, FactSpace, Verdict,
    subsume_across, subsume_antecedent,
)
from loomground_solver.causal_construction import PresupposedLink
from loomground_solver.dimensions import Dimension
from loomground_solver.reasoning import Edge
from loomground_solver.relation import ESCALATE, RelationAlgebra
from loomground_solver.temporal import Date


# ── fixtures (fixed, dimension-tagged facts) ──────────────────────────────────

def _structural_edges() -> tuple[Edge, ...]:
    # controller —is-a→ processor —is-a→ actor  (a 2-hop is-a chain)
    return (
        Edge("controller", "is-a", "processor", Dimension.STRUCTURAL),
        Edge("processor", "is-a", "actor", Dimension.STRUCTURAL),
        Edge("engine", "part-of", "car", Dimension.STRUCTURAL),
    )


def _causal_edges() -> tuple[Edge, ...]:
    # overload —causes→ failure  (GROUNDED, STATED+grounded shape)
    return (Edge("overload", "causes", "failure", Dimension.CAUSAL, weight=0.9),)


def _relation_algebra() -> RelationAlgebra:
    # A settled chain (owns∘controls → controls) and a contested one
    # (licenses∘sublicenses → ESCALATE).
    vocab = {"owns", "controls", "licenses", "sublicenses"}
    table = {
        ("owns", "controls"): "controls",
        ("licenses", "sublicenses"): ESCALATE,
    }
    return RelationAlgebra(vocabulary=vocab, table=table)


# ── 1. STRUCTURAL: reachable over is-a edges → SATISFIED ───────────────────────

def test_structural_reachable_satisfied():
    cond = Condition(name="is-actor", dimension=Dimension.STRUCTURAL,
                     subject="controller", object="actor")
    v = subsume_across(cond, FactSpace(structural_edges=_structural_edges()))
    assert v.verdict is Verdict.SATISFIED
    assert v.dimension is Dimension.STRUCTURAL
    assert len(v.evidence) == 2      # controller→processor→actor


def test_structural_unreachable_not_satisfied():
    cond = Condition(name="is-car", dimension=Dimension.STRUCTURAL,
                     subject="controller", object="car")
    v = subsume_across(cond, FactSpace(structural_edges=_structural_edges()))
    assert v.verdict is Verdict.NOT_SATISFIED     # closed-world: unproven ≠ satisfied


# ── 1b. STRUCTURAL incompleteness → OPEN (mirror of incomplete_causal) ─────────
# An unreachable target is normally NOT_SATISFIED (closed-world), but when the
# taxonomy at the subject is FLAGGED incomplete, absence of a path is not proof
# of non-subsumption → OPEN. Backward-compatible: no flag ⇒ NOT_SATISFIED.

def test_structural_incomplete_node_opens():
    cond = Condition(name="is-car", dimension=Dimension.STRUCTURAL,
                     subject="controller", object="car")
    v = subsume_across(cond, FactSpace(structural_edges=_structural_edges(),
                                       incomplete_structural=("controller",)))
    assert v.verdict is Verdict.OPEN              # node's neighbourhood flagged incomplete


def test_structural_incomplete_pair_opens():
    cond = Condition(name="is-car", dimension=Dimension.STRUCTURAL,
                     subject="controller", object="car")
    v = subsume_across(cond, FactSpace(structural_edges=_structural_edges(),
                                       incomplete_structural=(("controller", "car"),)))
    assert v.verdict is Verdict.OPEN


def test_structural_incomplete_unrelated_flag_still_denies():
    # a flag on a DIFFERENT node/pair does not open this condition (still closed-world)
    cond = Condition(name="is-car", dimension=Dimension.STRUCTURAL,
                     subject="controller", object="car")
    v = subsume_across(cond, FactSpace(structural_edges=_structural_edges(),
                                       incomplete_structural=("engine", ("x", "y"))))
    assert v.verdict is Verdict.NOT_SATISFIED


def test_structural_grounded_path_wins_over_incomplete_flag():
    # a real path is SATISFIED even if the node is also flagged incomplete
    cond = Condition(name="is-actor", dimension=Dimension.STRUCTURAL,
                     subject="controller", object="actor")
    v = subsume_across(cond, FactSpace(structural_edges=_structural_edges(),
                                       incomplete_structural=("controller",)))
    assert v.verdict is Verdict.SATISFIED


def test_structural_incomplete_false_object_is_ignored():
    from types import SimpleNamespace
    mark = SimpleNamespace(subject="controller", object="car", incomplete=False)
    cond = Condition(name="is-car", dimension=Dimension.STRUCTURAL,
                     subject="controller", object="car")
    v = subsume_across(cond, FactSpace(structural_edges=_structural_edges(),
                                       incomplete_structural=(mark,)))
    assert v.verdict is Verdict.NOT_SATISFIED     # explicit incomplete=False ⇒ not opened


# ── 2. RELATIONAL: composed via RelationAlgebra ───────────────────────────────

def test_relational_chain_satisfied_via_algebra():
    cond = Condition(name="controls", dimension=Dimension.RELATIONAL,
                     chain=("owns", "controls"), expect="controls")
    v = subsume_across(cond, FactSpace(relations=_relation_algebra()))
    assert v.verdict is Verdict.SATISFIED
    assert v.evidence["composed"] == "controls"


def test_relational_contested_chain_open():
    cond = Condition(name="sublic", dimension=Dimension.RELATIONAL,
                     chain=("licenses", "sublicenses"), expect="licenses")
    v = subsume_across(cond, FactSpace(relations=_relation_algebra()))
    assert v.verdict is Verdict.OPEN              # ESCALATE sentinel → OPEN


# ── 3. TEMPORAL: date comparison ──────────────────────────────────────────────

def test_temporal_deadline_met_satisfied():
    cond = Condition(name="in-time", dimension=Dimension.TEMPORAL,
                     temporal=("on_or_before", Date("2026-03-01"), Date("2026-03-31")))
    v = subsume_across(cond, FactSpace())
    assert v.verdict is Verdict.SATISFIED


def test_temporal_deadline_missed_not_satisfied():
    cond = Condition(name="late", dimension=Dimension.TEMPORAL,
                     temporal=("on_or_before", Date("2026-04-15"), Date("2026-03-31")))
    v = subsume_across(cond, FactSpace())
    assert v.verdict is Verdict.NOT_SATISFIED


def test_temporal_unresolved_operand_open():
    # The anchoring event date is unknown (None) — surface the gap, never guess.
    cond = Condition(name="unresolved", dimension=Dimension.TEMPORAL,
                     temporal=("on_or_before", None, Date("2026-03-31")))
    v = subsume_across(cond, FactSpace())
    assert v.verdict is Verdict.OPEN


# ── 4. CAUSAL: grounded vs presupposed ────────────────────────────────────────

def test_causal_grounded_link_satisfied_via_classification():
    # No explicit dimension — routed CAUSAL by the "why … cause" query cue.
    cond = Condition(name="overload-causes-failure",
                     text="why does overload cause failure",
                     subject="overload", object="failure")
    v = subsume_across(cond, FactSpace(causal_edges=_causal_edges()))
    assert v.dimension is Dimension.CAUSAL        # classify_query_dimension routed it
    assert v.verdict is Verdict.SATISFIED


def test_causal_presupposed_link_open():
    # The link is only PRESUPPOSED by construction (incomplete) — not grounded.
    presupposed = PresupposedLink(cause="stress", effect="failure",
                                  mechanism="fatigue", load_bearing=True)
    cond = Condition(name="stress-causes-failure", dimension=Dimension.CAUSAL,
                     subject="stress", object="failure")
    facts = FactSpace(causal_edges=_causal_edges(),
                      incomplete_causal=(presupposed,))
    v = subsume_across(cond, facts)
    assert v.verdict is Verdict.OPEN              # incompleteness propagates → OPEN


# ── 5. unclassifiable dimension → OPEN ────────────────────────────────────────

def test_unclassifiable_dimension_open():
    cond = Condition(name="mystery", text="elephant velvet ranges quietly")
    v = subsume_across(cond, FactSpace())
    assert v.dimension is None
    assert v.verdict is Verdict.OPEN              # never guessed


# ── 6. INTENTIONAL / closed-world ─────────────────────────────────────────────

def test_intentional_closed_world_unproven_not_satisfied():
    cond = Condition(name="open-textured", dimension=Dimension.INTENTIONAL,
                     literal="fair-and-lawful")
    v = subsume_across(cond, FactSpace(literals=frozenset({"processing"})))
    assert v.verdict is Verdict.NOT_SATISFIED     # unproven ≠ true

    # ...unless an injected judge (the existing seam) decides the open literal.
    judge = lambda lit, facts: lit == "fair-and-lawful"
    v2 = subsume_across(cond, FactSpace(literals=frozenset({"processing"})), judge=judge)
    assert v2.verdict is Verdict.SATISFIED


# ── 7. antecedent aggregation (AND, escalation dominant) ──────────────────────

def test_antecedent_all_satisfied():
    facts = FactSpace(structural_edges=_structural_edges(),
                      causal_edges=_causal_edges(),
                      literals=frozenset({"fair-and-lawful"}))
    conds = [
        Condition(name="is-actor", dimension=Dimension.STRUCTURAL,
                  subject="controller", object="actor"),
        Condition(name="overload-fail", dimension=Dimension.CAUSAL,
                  subject="overload", object="failure"),
        Condition(name="lawful", dimension=Dimension.INTENTIONAL,
                  literal="fair-and-lawful"),
    ]
    a = subsume_antecedent(conds, facts)
    assert a.verdict is Verdict.SATISFIED
    assert len(a.conditions) == 3


def test_antecedent_one_open_makes_whole_open():
    presupposed = PresupposedLink(cause="stress", effect="failure", load_bearing=True)
    facts = FactSpace(structural_edges=_structural_edges(),
                      incomplete_causal=(presupposed,))
    conds = [
        Condition(name="is-actor", dimension=Dimension.STRUCTURAL,
                  subject="controller", object="actor"),          # SATISFIED
        Condition(name="stress-fail", dimension=Dimension.CAUSAL,
                  subject="stress", object="failure"),            # OPEN (presupposed)
    ]
    a = subsume_antecedent(conds, facts)
    assert a.verdict is Verdict.OPEN                              # one OPEN → antecedent OPEN
    assert "stress-fail" in a.reason


def test_antecedent_not_satisfied_when_a_condition_fails_and_none_open():
    facts = FactSpace(structural_edges=_structural_edges())
    conds = [
        Condition(name="is-actor", dimension=Dimension.STRUCTURAL,
                  subject="controller", object="actor"),          # SATISFIED
        Condition(name="is-car", dimension=Dimension.STRUCTURAL,
                  subject="controller", object="car"),            # NOT_SATISFIED
    ]
    a = subsume_antecedent(conds, facts)
    assert a.verdict is Verdict.NOT_SATISFIED
