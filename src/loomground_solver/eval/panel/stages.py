# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Concrete panel stages — each one drives ONE real solver evaluator.

A stage is the panel's unit of *computation*: it takes typed inputs and returns
a :class:`core.StageOutcome` whose :class:`~cross_subsumption.Verdict` was
produced by a genuine engine call, never asserted. The runner folds those
verdicts through the engine's own OPEN-dominant aggregation — so a case's
terminal state is *computed*, then *graded* against the author's expectation,
never hand-set to match it.

The stages map one-to-one onto the modules the 2026-08-06 GDPR e2e exercised:

  * :class:`IntentionalCondition` → :func:`cross_subsumption.subsume_across`
    (closed-world / open-textured — scope gating, element firing);
  * :class:`StructuralCondition`  → ``subsume_across`` STRUCTURAL route
    (is-a / part-of reachability; taxonomy-incomplete → OPEN);
  * :class:`TemporalOrder`        → ``subsume_across`` TEMPORAL route (date
    ordering);
  * :class:`QuantThreshold`       → :func:`quantitative.evaluate_quantitative`
    (numeric / duration thresholds — the 72-hour deadline);
  * :class:`StandardApplication`  → :func:`standard_eval.evaluate_standard`
    (open-textured standard; contested → escalate → OPEN);
  * :class:`EpistemicPremise`     → :func:`epistemic_status.propagate_premises`
    (settledness; presupposed / contested → OPEN);
  * :class:`DeonticResolution`    → :func:`api.derive` /
    ``.resolution_for`` (norm-conflict resolution; genuine collision → OPEN) —
    also the source of the signed :func:`replay.verify_trace` artifact;
  * :class:`HonestGap`            → a node whose evaluator is not in panel scope
    yet: it returns OPEN by construction ("a gap becomes a backlog item, not a
    faked pass").

No stage imports ``loomground_legal`` / ``loomground_versum``; all reasoning is
pure-solver.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional, Sequence

from ... import derive as _derive
from ...cross_subsumption import (
    Condition, FactSpace, Verdict, subsume_across,
)
from ...dimensions import Dimension
from ...epistemic_status import EpistemicStatus, StatusedPremise, propagate_premises
from ...predicate import Predicate
from ...quantitative import QuantCondition, evaluate_quantitative
from ...reasoning import Edge
from ...rulepacks import GENERIC_PACK, LEX_CONFLICT_PACK
from ...scenario import Norm, Scenario
from ...standard_eval import StubModel, evaluate_standard
from ...temporal import Date, Duration, Money
from .core import Stage, StageOutcome

__all__ = [
    "IntentionalCondition", "StructuralCondition", "TemporalOrder",
    "QuantThreshold", "StandardApplication", "EpistemicPremise",
    "DeonticResolution", "HonestGap",
    "is_a", "money", "duration",
]


# ── small construction helpers authors reuse ──────────────────────────────────

def is_a(child: str, parent: str) -> Edge:
    """A STRUCTURAL is-a edge for :class:`StructuralCondition`."""
    return Edge(subject=child, predicate="is_a", object=parent,
                dimension=Dimension.STRUCTURAL)


def money(amount: str | int, currency: str) -> Money:
    """A typed, Decimal-safe currency amount (never a float)."""
    return Money(amount=Decimal(str(amount)), currency=currency)


def duration(**kw: int) -> Duration:
    """A typed duration, e.g. ``duration(hours=96)``."""
    return Duration(**kw)


# ── 1. INTENTIONAL / closed-world condition ───────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class IntentionalCondition(Stage):
    """A closed-world / open-textured condition via ``subsume_across``.

    ``literal`` is the element to test; ``present`` is the set of grounded
    literals that hold. Closed-world: a literal absent from ``present`` is
    NOT_SATISFIED, never fabricated true. Used for scope gating and element
    firing (e.g. ``"targets_eu_data_subjects" ∈ facts`` → SATISFIED).
    """

    literal: str
    present: Sequence[str] = ()
    dimension: str = Dimension.INTENTIONAL.value

    def evaluate(self) -> StageOutcome:
        cond = Condition(name=self.name, literal=self.literal,
                         dimension=Dimension.INTENTIONAL)
        dv = subsume_across(cond, FactSpace(literals=frozenset(self.present)))
        return StageOutcome(dv.verdict, dv.reason, fact_text=self.literal,
                            evidence=dv.evidence)


# ── 2. STRUCTURAL reachability condition ──────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class StructuralCondition(Stage):
    """A structural is-a / part-of subsumption via ``subsume_across``.

    ``subject`` reaches ``object`` over the ``edges`` (build with :func:`is_a`).
    A target unreachable under a *known-incomplete* taxonomy region
    (``incomplete_nodes`` / ``incomplete_pairs``) is OPEN, not denied.
    """

    subject: str
    object: str
    edges: Sequence[Edge] = ()
    incomplete_nodes: Sequence[str] = ()
    incomplete_pairs: Sequence[tuple] = ()
    dimension: str = Dimension.STRUCTURAL.value

    def evaluate(self) -> StageOutcome:
        cond = Condition(name=self.name, subject=self.subject,
                         object=self.object, dimension=Dimension.STRUCTURAL)
        facts = FactSpace(
            structural_edges=tuple(self.edges),
            incomplete_structural=tuple(self.incomplete_nodes)
            + tuple(self.incomplete_pairs),
        )
        dv = subsume_across(cond, facts)
        return StageOutcome(dv.verdict, dv.reason,
                            fact_text=f"{self.subject} is-a {self.object}",
                            evidence=dv.evidence)


# ── 3. TEMPORAL ordering condition ────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class TemporalOrder(Stage):
    """A date-ordering condition via ``subsume_across`` TEMPORAL.

    ``op`` in {before, after, on_or_before, on_or_after}; ``left`` / ``right``
    are ISO date strings (an unresolved / ``None`` operand → OPEN).
    """

    op: str
    left: Optional[str]
    right: Optional[str]
    dimension: str = Dimension.TEMPORAL.value

    def evaluate(self) -> StageOutcome:
        left = Date(self.left) if self.left else None
        right = Date(self.right) if self.right else None
        cond = Condition(name=self.name, dimension=Dimension.TEMPORAL,
                         temporal=(self.op, left, right))
        dv = subsume_across(cond, FactSpace())
        return StageOutcome(dv.verdict, dv.reason,
                            fact_text=f"{self.left} {self.op} {self.right}",
                            evidence=dv.evidence)


# ── 4. QUANTITATIVE threshold condition ───────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class QuantThreshold(Stage):
    """A numeric / duration threshold via ``quantitative.evaluate_quantitative``.

    ``comparator`` + ``value`` (+ ``unit``) form the bound; ``operand`` is the
    measured quantity (a :class:`temporal.Money`, :class:`temporal.Duration`, or
    a number — build with :func:`money` / :func:`duration`). A missing /
    incommensurable / calendar-ambiguous operand → OPEN.
    """

    comparator: str
    value: str
    unit: Optional[str] = None
    operand: Any = None
    subject_ref: str = "operand"

    def evaluate(self) -> StageOutcome:
        pred = Predicate(kind="threshold", subject_ref=self.subject_ref,
                         comparator=self.comparator, value=str(self.value),
                         unit=self.unit)
        cond = QuantCondition(name=self.name, predicate=pred,
                              subject_ref=self.subject_ref)
        dv = evaluate_quantitative(cond, {self.subject_ref: self.operand})
        return StageOutcome(dv.verdict, dv.reason,
                            fact_text=f"{self.subject_ref} {self.comparator} "
                                      f"{self.value} {self.unit or ''}".strip(),
                            evidence=dv.evidence)


# ── 5. OPEN-STANDARD application ───────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class StandardApplication(Stage):
    """An open-textured standard via ``standard_eval.evaluate_standard``.

    ``standard`` is the yardstick ("unlikely to result in a risk"); ``facts`` is
    the facts text; ``proposal`` is the (stub-model) proposed application — a
    dict with ``benchmark`` / ``relied_on`` / ``verdict`` / ``met`` /
    ``contested`` (see :class:`standard_eval.StandardProposal`). A contested,
    ungrounded, unsound or sub-floor proposal escalates/rejects → OPEN; a clean
    application answers SATISFIED / NOT_SATISFIED. The spans in ``proposal`` must
    be verbatim substrings of ``facts`` or the honesty floor rejects them.
    """

    standard: str
    facts: str
    proposal: dict
    dimension: str = Dimension.INTENTIONAL.value

    def evaluate(self) -> StageOutcome:
        res = evaluate_standard(self.standard, self.facts,
                                model=StubModel(self.proposal))
        if res.status == "satisfied":
            verdict = Verdict.SATISFIED
        elif res.status == "not_satisfied":
            verdict = Verdict.NOT_SATISFIED
        else:  # escalated | rejected → honest OPEN
            verdict = Verdict.OPEN
        return StageOutcome(verdict, f"[{res.status}] {res.reason}",
                            fact_text=self.standard,
                            evidence={"status": res.status,
                                      "benchmark": res.benchmark})


# ── 6. EPISTEMIC premise settledness ──────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class EpistemicPremise(Stage):
    """A premise's *settledness* via ``epistemic_status.propagate_premises``.

    ``status`` is an :class:`epistemic_status.EpistemicStatus`. SETTLED
    {ASSERTED, INFERRED} → SATISFIED (available to rest on); UNSETTLED
    {PRESUPPOSED, CONTESTED, UNKNOWN} → OPEN (escalate). This is the channel by
    which a *presupposed* liability-founding fact makes the whole issue OPEN.
    A stage carrying an UNSETTLED status should also carry an ``incomplete``
    :class:`Grounding` — the two say the same honest thing on two axes.
    """

    status: EpistemicStatus

    def evaluate(self) -> StageOutcome:
        agg = propagate_premises([StatusedPremise(name=self.name,
                                                  status=self.status)])
        return StageOutcome(agg.overall, agg.reason,
                            fact_text=f"premise {self.name} is {self.status.value}",
                            evidence={"status": self.status.value})


# ── 7. DEONTIC conflict resolution (+ the signed-replay artifact) ─────────────

@dataclass(frozen=True, kw_only=True)
class DeonticResolution(Stage):
    """A norm-conflict resolution via the real deontic solver (``api.derive``).

    ``norms`` is a list of ``(act, modality, source[, specificity, rank])``
    tuples; the runner derives the scenario under ``pack`` and reads
    ``resolution_for(act)``. A genuine collision with no ordering →
    ``status == 'open'`` → OPEN (escalate); a lex-resolved obligation/permission
    → SATISFIED; a prohibition → NOT_SATISFIED.

    This is also the panel's source of the **signed-replay artifact**: the
    derivation's :meth:`trace` and its :class:`Scenario` are exposed on the
    outcome so the runner can thread them into :func:`grading.grade_run` and
    :func:`replay.verify_trace` scores an intact trace as PASS.

    Default pack is :data:`rulepacks.GENERIC_PACK` (which escalates a genuine
    collision); pass ``pack="lex"`` for :data:`rulepacks.LEX_CONFLICT_PACK`.
    """

    norms: Sequence[tuple]
    act: str
    pack: str = "generic"

    def _scenario(self) -> Scenario:
        built = []
        for spec in self.norms:
            act, modality, source = spec[0], spec[1], spec[2]
            specificity = spec[3] if len(spec) > 3 else 0
            rank = spec[4] if len(spec) > 4 else 0
            built.append(Norm(act, modality, source=source,
                              specificity=specificity, rank=rank))
        return Scenario("panel", norms=built)

    def _pack(self):
        return LEX_CONFLICT_PACK if self.pack == "lex" else GENERIC_PACK

    def evaluate(self) -> StageOutcome:
        sc = self._scenario()
        pack = self._pack()
        derived = _derive(sc, pack=pack)
        res = derived.resolution_for(self.act)
        if res.status == "open":
            verdict = Verdict.OPEN
        elif res.verdict in ("prohibited", "forbidden"):
            verdict = Verdict.NOT_SATISFIED
        else:
            verdict = Verdict.SATISFIED
        return StageOutcome(
            verdict,
            f"deontic resolution of {self.act!r}: status={res.status}, "
            f"verdict={res.verdict}, collisions={list(res.collisions)}",
            fact_text=f"deontic({self.act})",
            evidence={"scenario": sc, "trace": derived.trace(), "pack": pack,
                      "status": res.status, "verdict": res.verdict})


# ── 8. HONEST GAP — an out-of-scope node opens, never fakes a pass ────────────

@dataclass(frozen=True, kw_only=True)
class HonestGap(Stage):
    """A node whose evaluator is not in panel scope: OPEN by construction.

    The discipline from the plan — "if a corpus case needs an operation that
    isn't built, the honest outcome is ESCALATE; a gap becomes a new backlog
    item, not a faked pass." Its :class:`Grounding` should be ``incomplete``.
    """

    reason_text: str = "evaluator not in panel scope"

    def evaluate(self) -> StageOutcome:
        return StageOutcome(Verdict.OPEN,
                            f"{self.reason_text} → OPEN (honest gap, not a faked pass)",
                            fact_text=self.name)
