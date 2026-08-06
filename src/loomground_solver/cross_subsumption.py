# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Cross-dimensional subsumption — evaluate one norm condition (and a whole
antecedent) across the five reasoning dimensions, honestly.

Ordinary :mod:`subsumption` decides a condition against a *flat* set of literals
under a closed-world default. That is exactly right for the INTENTIONAL /
open-textured dimension, and wrong for the other four: a *structural* condition
("X is a Y") is decided by reachability over is-a / part-of edges; a *causal*
condition ("X causes Y") by presence in the **grounded** causal edges; a
*temporal* condition ("done before the deadline") by a date comparison; a
*relational* condition ("A is linked to C") by composing the relation chain.
Feeding any of those to plain ``holds`` would silently answer *unproven → not
satisfied*, hiding the fact that the right evaluator was never run.

This op is a **router + evaluator** over already-grounded, dimension-tagged
facts. It is deterministic [D]: it takes facts, not model proposals — there is no
``ModelFn`` and no stub model here. (A borderline INTENTIONAL classification may
optionally escalate through the existing :func:`subsumption.holds` ``judge``
seam; no new model seam is introduced.)

It **consumes** the substrate rather than regrowing it:

  * :func:`subsumption.holds` — the closed-world classifier (INTENTIONAL / else);
  * :class:`dimensions.Dimension` + :func:`dimensions.classify_query_dimension`
    — the dimension model and the query-cue router;
  * :class:`relation.RelationAlgebra` + :data:`relation.ESCALATE` — relational
    chain composition and its escalate-don't-guess sentinel;
  * :class:`reasoning.Edge` — the dimensioned fact/edge type traversed for the
    structural and causal routes;
  * :mod:`temporal` (:class:`temporal.Date`) — the typed date comparison.

Honesty is committed, not optional:

  1. **route, don't guess** — each condition is routed to its dimension's
     evaluator (explicit ``dimension`` wins, else
     :func:`dimensions.classify_query_dimension`).
  2. **incompleteness propagates** — a condition that rests on a fact *flagged
     incomplete by construction* (a PRESUPPOSED causal link; see
     :mod:`causal_construction`) is ``OPEN``, never counted satisfied. The
     incompleteness of construction propagates into reasoning.
  3. **unclassifiable → OPEN** — a condition whose dimension cannot be
     determined is ``OPEN``, never guessed at.
  4. **antecedent AND** — an antecedent is the AND of its conditions; **any**
     ``OPEN`` condition makes the whole antecedent ``OPEN`` (escalate).
  5. **closed-world** — an unproven condition is ``NOT_SATISFIED``, never
     fabricated true.

``OPEN`` (escalate) is a first-class, correct verdict — the honest answer when a
condition is contested, unresolved, unclassifiable, or rests on something the
construction only presupposed.

Pure stdlib. No governance, no corpus, no domain: inputs are a generic
:class:`Condition` and a :class:`FactSpace`. This module imports neither
``loomground_legal`` nor ``loomground_versum``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from .dimensions import Dimension, classify_query_dimension
from .reasoning import Edge, compose_paths
from .relation import ESCALATE, RelationAlgebra
from .subsumption import Judge, holds
from .temporal import Date


# ── verdicts ──────────────────────────────────────────────────────────────────

class Verdict(str, Enum):
    """The three outcomes a condition (or antecedent) can carry.

    ``OPEN`` is the escalate verdict — a first-class, correct answer, not a
    failure to decide. It is returned when a condition is contested, temporally
    unresolved, of an undeterminable dimension, or rests on an incomplete fact.
    """

    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    OPEN = "open"


#: Comparison operators for a temporal condition. ``left`` is compared to
#: ``right`` under the operator; both operands must be resolved
#: :class:`temporal.Date` values, else the condition is OPEN (unresolved).
_TEMPORAL_OPS = ("before", "after", "on_or_before", "on_or_after")


# ── inputs ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Condition:
    """One antecedent condition, evaluable across the 5 dimensions.

    A condition names *what* it asks and, when known, *which dimension* answers
    it. The dimension is taken from ``dimension`` when given, else inferred from
    ``text`` via :func:`dimensions.classify_query_dimension`. When neither
    settles a dimension the condition is OPEN (unclassifiable).

    The dimension-specific payload is read only by the matching evaluator:

      * INTENTIONAL / else — ``literal``: the closed-world literal for
        :func:`subsumption.holds`;
      * STRUCTURAL / CAUSAL — ``subject`` → ``object``: the endpoints to reach /
        the causal link to find;
      * TEMPORAL — ``temporal``: ``(op, left, right)`` with ``op`` in
        :data:`_TEMPORAL_OPS` and operands :class:`temporal.Date` or ``None``;
      * RELATIONAL — ``chain`` composed via the :class:`FactSpace` algebra, and
        ``expect``: the relation the chain must yield.
    """

    name: str = ""
    text: str = ""
    dimension: Optional[Dimension] = None
    # INTENTIONAL / else:
    literal: str = ""
    # STRUCTURAL / CAUSAL:
    subject: str = ""
    object: str = ""
    # TEMPORAL:
    temporal: Optional[Tuple[str, Optional[Date], Optional[Date]]] = None
    # RELATIONAL:
    chain: Tuple[Any, ...] = ()
    expect: Any = None

    def label(self) -> str:
        return self.name or self.text or self.literal or f"{self.subject}->{self.object}"


@dataclass(frozen=True)
class FactSpace:
    """The already-grounded, dimension-tagged fact bundle a condition is read
    against. Each field is the evidence base for one dimension; an evaluator
    touches only its own field.

    ``incomplete_causal`` is the honest-open channel: the causal links a
    construction *presupposed* but never grounded (a
    :class:`causal_construction.PresupposedLink`, or a plain ``(cause, effect)``
    pair). A causal condition matching one of these — and nothing grounded — is
    OPEN, so the incompleteness of construction propagates into reasoning.

    ``incomplete_structural`` is the same honest-open channel for the STRUCTURAL
    dimension: a taxonomy region the construction knows is under-specified. A
    structural condition whose target is unreachable is normally NOT_SATISFIED
    (closed-world: unproven ≠ satisfied), but if the subsumption ``(subject,
    object)`` — or the whole neighbourhood of ``subject`` — is flagged here, the
    verdict is OPEN instead: absence of a path is not proof of non-subsumption
    when the taxonomy itself is known-incomplete. Marks are ``(subject, object)``
    pairs, bare ``subject`` strings, or objects exposing ``subject``/``object``
    (mirrors ``incomplete_causal``).
    """

    literals: frozenset = frozenset()                # closed-world facts (INTENTIONAL/else)
    structural_edges: Tuple[Edge, ...] = ()          # is-a / part-of (STRUCTURAL)
    causal_edges: Tuple[Edge, ...] = ()              # GROUNDED cause→effect (CAUSAL)
    incomplete_causal: Tuple[Any, ...] = ()          # presupposed/incomplete causal links
    incomplete_structural: Tuple[Any, ...] = ()      # known-incomplete taxonomy → OPEN not deny
    relations: Optional[RelationAlgebra] = None      # the relation algebra (RELATIONAL)


# ── outputs ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DimVerdict:
    """The verdict on one condition: the dimension it was routed to, the
    verdict, the evidence that settled it, and a human-readable reason."""

    condition: str
    dimension: Optional[Dimension]
    verdict: Verdict
    evidence: Any = None
    reason: str = ""

    @property
    def satisfied(self) -> bool:
        return self.verdict is Verdict.SATISFIED

    @property
    def open(self) -> bool:
        return self.verdict is Verdict.OPEN


@dataclass(frozen=True)
class AntecedentVerdict:
    """The verdict on a whole antecedent (AND across conditions), carrying every
    per-condition :class:`DimVerdict`. Any OPEN condition makes the antecedent
    OPEN; else all-SATISFIED is SATISFIED, otherwise NOT_SATISFIED."""

    verdict: Verdict
    conditions: Tuple[DimVerdict, ...]
    reason: str = ""

    @property
    def open(self) -> bool:
        return self.verdict is Verdict.OPEN

    @property
    def satisfied(self) -> bool:
        return self.verdict is Verdict.SATISFIED


# ── incomplete-fact normalisation ─────────────────────────────────────────────

def _incomplete_pairs(marks: Iterable[Any]) -> frozenset:
    """Normalise the incomplete-causal markers to ``(cause, effect)`` pairs.

    Accepts :class:`causal_construction.PresupposedLink`-shaped objects (any
    object exposing ``cause`` / ``effect`` attributes and a truthy
    ``incomplete``) and plain ``(cause, effect)`` tuples. An object that carries
    an explicit ``incomplete = False`` is *not* treated as incomplete — only a
    genuinely-flagged fact opens a condition."""
    out: set = set()
    for m in marks or ():
        if isinstance(m, (tuple, list)) and len(m) >= 2:
            out.add((m[0], m[1]))
            continue
        cause = getattr(m, "cause", None)
        effect = getattr(m, "effect", None)
        incomplete = getattr(m, "incomplete", True)
        if cause is not None and effect is not None and incomplete:
            out.add((cause, effect))
    return frozenset(out)


def _incomplete_structural(marks: Iterable[Any]) -> Tuple[frozenset, frozenset]:
    """Normalise incomplete-structural markers to ``(pairs, nodes)``.

    Two granularities, both meaning "the taxonomy here may be incomplete, so an
    unreachable target should OPEN rather than be denied":

      * a ``(subject, object)`` pair — a specific subsumption the construction
        presupposed but never grounded (mirrors :func:`_incomplete_pairs`);
      * a bare ``subject`` string, or an object exposing ``subject``/``node``
        with no ``object`` — the whole structural neighbourhood of that node is
        flagged, so ANY unreachable target from it opens.

    An object carrying an explicit ``incomplete = False`` is ignored — only a
    genuinely-flagged region opens a condition."""
    pairs: set = set()
    nodes: set = set()
    for m in marks or ():
        if isinstance(m, str):
            nodes.add(m)
            continue
        if isinstance(m, (tuple, list)) and len(m) >= 2:
            pairs.add((m[0], m[1]))
            continue
        if getattr(m, "incomplete", True) is False:
            continue
        subject = getattr(m, "subject", None)
        if subject is None:
            subject = getattr(m, "node", None)
        obj = getattr(m, "object", None)
        if subject is not None and obj is not None:
            pairs.add((subject, obj))
        elif subject is not None:
            nodes.add(subject)
    return frozenset(pairs), frozenset(nodes)


# ── per-dimension evaluators ──────────────────────────────────────────────────

def _reachable(edges: Sequence[Edge], src: str, dst: str) -> Optional[list]:
    """Reachability over STRUCTURAL edges (is-a / part-of): the predicate path
    from ``src`` to ``dst``, or ``None`` if unreachable.

    The acyclic multi-hop walk is **consumed** from
    :func:`reasoning.compose_paths` — the package's one canonical path enumerator
    — never re-grown here. Only STRUCTURAL-tagged edges are handed to it, so a
    causal edge cannot smuggle a structural conclusion; ``min_hops=1`` also admits
    the direct edge, and ``max_depth`` is bounded by the edge count so any acyclic
    path is found. The evidence returned is the per-hop ``src -pred-> dst`` chain
    of the shortest qualifying path (deterministic), preserving the historical
    shape."""
    if src == dst:
        return []
    structural = [e for e in edges if e.dimension is Dimension.STRUCTURAL]
    if not structural:
        return None
    n = len(structural)
    paths = compose_paths(structural, start=src, min_hops=1,
                          max_depth=max(2, n), max_results=max(200, n * n))
    reaching = [inf for inf in paths if inf.object == dst]
    if not reaching:
        return None
    best = min(reaching, key=lambda inf: inf.hops)   # shortest → stable evidence
    return [f"{h['subject']} -{h['predicate']}-> {h['object']}" for h in best.path]


def _eval_structural(cond: Condition, facts: FactSpace) -> DimVerdict:
    path = _reachable(facts.structural_edges, cond.subject, cond.object)
    if path is not None:
        return DimVerdict(cond.label(), Dimension.STRUCTURAL, Verdict.SATISFIED,
                          evidence=path,
                          reason=f"{cond.subject} reaches {cond.object} over structural edges")
    pairs, nodes = _incomplete_structural(facts.incomplete_structural)
    if (cond.subject, cond.object) in pairs or cond.subject in nodes:
        return DimVerdict(cond.label(), Dimension.STRUCTURAL, Verdict.OPEN,
                          evidence=(cond.subject, cond.object),
                          reason=f"no grounded structural path {cond.subject} → "
                                 f"{cond.object}, but the taxonomy at {cond.subject} is "
                                 "flagged incomplete — absence of a path is not proof of "
                                 "non-subsumption → OPEN (incompleteness propagates)")
    return DimVerdict(cond.label(), Dimension.STRUCTURAL, Verdict.NOT_SATISFIED,
                      evidence=None,
                      reason=f"no structural path {cond.subject} → {cond.object} "
                             f"(closed-world: unproven ≠ satisfied)")


def _eval_causal(cond: Condition, facts: FactSpace) -> DimVerdict:
    for e in facts.causal_edges:
        if e.dimension is Dimension.CAUSAL and e.subject == cond.subject \
                and e.object == cond.object:
            return DimVerdict(cond.label(), Dimension.CAUSAL, Verdict.SATISFIED,
                              evidence=e,
                              reason=f"grounded causal edge {e.subject} →[{e.predicate}]→ {e.object}")
    if (cond.subject, cond.object) in _incomplete_pairs(facts.incomplete_causal):
        return DimVerdict(cond.label(), Dimension.CAUSAL, Verdict.OPEN,
                          evidence=(cond.subject, cond.object),
                          reason="rests on a PRESUPPOSED/incomplete causal link — "
                                 "the statute assumes it but never grounds it; "
                                 "incompleteness of construction propagates → OPEN")
    return DimVerdict(cond.label(), Dimension.CAUSAL, Verdict.NOT_SATISFIED,
                      evidence=None,
                      reason=f"no grounded causal link {cond.subject} → {cond.object} "
                             f"(closed-world: unproven ≠ satisfied)")


def _eval_temporal(cond: Condition, facts: FactSpace) -> DimVerdict:
    spec = cond.temporal
    if not spec or len(spec) != 3:
        return DimVerdict(cond.label(), Dimension.TEMPORAL, Verdict.OPEN,
                          reason="temporal condition without an (op, left, right) spec → OPEN")
    op, left, right = spec
    if op not in _TEMPORAL_OPS:
        return DimVerdict(cond.label(), Dimension.TEMPORAL, Verdict.OPEN,
                          reason=f"unknown temporal operator {op!r} → OPEN")
    if left is None or right is None:
        return DimVerdict(cond.label(), Dimension.TEMPORAL, Verdict.OPEN,
                          evidence=(op, left, right),
                          reason="a date operand is unresolved (incomplete) → OPEN, never guessed")
    if op == "before":
        ok = left < right
    elif op == "after":
        ok = right < left
    elif op == "on_or_before":
        ok = left <= right
    else:  # on_or_after
        ok = right <= left
    verdict = Verdict.SATISFIED if ok else Verdict.NOT_SATISFIED
    return DimVerdict(cond.label(), Dimension.TEMPORAL, verdict,
                      evidence=(op, left.iso, right.iso),
                      reason=f"{left.iso} {op} {right.iso} = {ok}")


def _eval_relational(cond: Condition, facts: FactSpace) -> DimVerdict:
    if facts.relations is None:
        return DimVerdict(cond.label(), Dimension.RELATIONAL, Verdict.OPEN,
                          reason="no relation algebra supplied → OPEN")
    result, escalated = facts.relations.compose_path(cond.chain)
    if escalated or result is ESCALATE:
        return DimVerdict(cond.label(), Dimension.RELATIONAL, Verdict.OPEN,
                          evidence={"chain": list(cond.chain), "composed": "ESCALATE"},
                          reason="relation chain is contested (ESCALATE) → OPEN, "
                                 "never a fabricated resolution")
    if result is not None and result == cond.expect:
        return DimVerdict(cond.label(), Dimension.RELATIONAL, Verdict.SATISFIED,
                          evidence={"chain": list(cond.chain), "composed": result},
                          reason=f"chain composes to {result!r} = expected")
    return DimVerdict(cond.label(), Dimension.RELATIONAL, Verdict.NOT_SATISFIED,
                      evidence={"chain": list(cond.chain), "composed": result},
                      reason=f"chain composes to {result!r} ≠ expected {cond.expect!r}")


def _eval_intentional(cond: Condition, facts: FactSpace,
                      judge: Optional[Judge]) -> DimVerdict:
    lit = cond.literal or cond.text
    ok = holds(lit, set(facts.literals), judge=judge)
    verdict = Verdict.SATISFIED if ok else Verdict.NOT_SATISFIED
    return DimVerdict(cond.label(), Dimension.INTENTIONAL, verdict,
                      evidence=lit,
                      reason=f"closed-world holds({lit!r}) = {ok}"
                             + ("" if ok else " (unproven ≠ satisfied)"))


# ── the op ────────────────────────────────────────────────────────────────────

def subsume_across(condition: Condition, facts: FactSpace, *,
                   dimension: Optional[Dimension] = None,
                   judge: Optional[Judge] = None) -> DimVerdict:
    """Evaluate ONE ``condition`` against ``facts``, routed by its dimension.

    The dimension is ``dimension`` if given, else ``condition.dimension``, else
    :func:`dimensions.classify_query_dimension` on ``condition.text``. When none
    of those settles a dimension the condition is **OPEN** (unclassifiable —
    never guessed). Otherwise it routes:

      * STRUCTURAL  → reachability over the structural (is-a / part-of) edges;
      * CAUSAL      → presence in the **grounded** causal edges (a
        presupposed/incomplete link → OPEN);
      * TEMPORAL    → :class:`temporal.Date` comparison (an unresolved operand →
        OPEN);
      * RELATIONAL  → :meth:`relation.RelationAlgebra.compose_path` (the
        :data:`relation.ESCALATE` sentinel / an escalated fold → OPEN);
      * INTENTIONAL / else → :func:`subsumption.holds` (closed-world; an optional
        ``judge`` may decide an open-textured literal).

    Returns a :class:`DimVerdict` carrying the dimension, verdict, evidence and
    reason. Closed-world throughout: an unproven condition is ``NOT_SATISFIED``,
    never fabricated true.
    """
    dim = dimension or condition.dimension
    if dim is None:
        dim = classify_query_dimension(condition.text)
    if dim is None:
        return DimVerdict(condition.label(), None, Verdict.OPEN,
                          reason="dimension undeterminable (no explicit dimension, "
                                 "no query cue) → OPEN, never guessed")
    dim = Dimension(dim)
    if dim is Dimension.STRUCTURAL:
        return _eval_structural(condition, facts)
    if dim is Dimension.CAUSAL:
        return _eval_causal(condition, facts)
    if dim is Dimension.TEMPORAL:
        return _eval_temporal(condition, facts)
    if dim is Dimension.RELATIONAL:
        return _eval_relational(condition, facts)
    # INTENTIONAL / else — the closed-world classifier.
    return _eval_intentional(condition, facts, judge)


def fold_verdicts(verdicts: Iterable[Verdict]) -> Verdict:
    """The canonical OPEN-dominant fold — the package's single weakest-link rule.

    Any ``OPEN`` → ``OPEN`` (escalation dominates, even over a NOT_SATISFIED
    sibling); else any ``NOT_SATISFIED`` → ``NOT_SATISFIED``; else ``SATISFIED``
    (an empty sequence is vacuously SATISFIED). Both :func:`subsume_antecedent`
    (folding per-condition :class:`DimVerdict`s) and
    :func:`issue_aggregation.aggregate_issues` (folding per-issue verdicts) reduce
    through this one function, so the OPEN-dominance rule is defined once and
    consumed everywhere rather than re-implemented per call site."""
    vs = list(verdicts)
    if any(v is Verdict.OPEN for v in vs):
        return Verdict.OPEN
    if any(v is Verdict.NOT_SATISFIED for v in vs):
        return Verdict.NOT_SATISFIED
    return Verdict.SATISFIED


def subsume_antecedent(conditions: Iterable[Condition], facts: FactSpace, *,
                       judge: Optional[Judge] = None) -> AntecedentVerdict:
    """Evaluate a whole antecedent — the AND of ``conditions`` — against
    ``facts``.

    Every condition is routed through :func:`subsume_across`. Aggregation is
    strict AND with escalation dominant:

      * **any** OPEN condition → the antecedent is **OPEN** (escalate): an
        antecedent resting on an open condition cannot be declared met *or*
        unmet;
      * else all SATISFIED → **SATISFIED**;
      * else (at least one NOT_SATISFIED, none OPEN) → **NOT_SATISFIED**.

    Every per-condition :class:`DimVerdict` is carried on the result, so the
    reason an antecedent opened or failed is always traceable to the condition
    that caused it.
    """
    verdicts = tuple(subsume_across(c, facts, judge=judge) for c in conditions)
    overall = fold_verdicts(v.verdict for v in verdicts)   # the one canonical fold
    if overall is Verdict.OPEN:
        opens = [v for v in verdicts if v.verdict is Verdict.OPEN]
        return AntecedentVerdict(
            overall, verdicts,
            reason=f"{len(opens)} condition(s) OPEN → antecedent OPEN (escalate): "
                   + "; ".join(v.condition for v in opens))
    if overall is Verdict.NOT_SATISFIED:
        unmet = [v for v in verdicts if v.verdict is Verdict.NOT_SATISFIED]
        return AntecedentVerdict(
            overall, verdicts,
            reason=f"{len(unmet)} condition(s) NOT_SATISFIED → antecedent not met: "
                   + "; ".join(v.condition for v in unmet))
    return AntecedentVerdict(
        overall, verdicts,
        reason="all conditions SATISFIED → antecedent met")
