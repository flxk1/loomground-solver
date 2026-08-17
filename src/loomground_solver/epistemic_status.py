# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Epistemic status — tag a premise with *how settled* it is, and let that
settledness propagate honestly into the verdict vocabulary the layer already
speaks.

:mod:`cross_subsumption` decides a condition *on the merits* — is it SATISFIED,
NOT_SATISFIED, or (escalate) OPEN. But a condition rests on premises, and a
premise can be more or less *settled* independently of whether it is, on the
merits, true: a fact may be flatly ASSERTED with a source, INFERRED from other
settled facts, merely PRESUPPOSED by the argument, actively CONTESTED between the
parties, or simply UNKNOWN. That axis — the *epistemic status* of a premise — is
orthogonal to merit, and this thin layer models exactly it.

It is a **tagging + propagation layer**, not a new engine. It does **one** thing
beyond attaching a status: it maps a status onto the *existing* honesty verdict
so an unsettled premise escalates rather than silently passing. It **consumes**,
never forks:

  * :class:`cross_subsumption.Verdict` — the three-valued honesty verdict
    (SATISFIED / NOT_SATISFIED / OPEN). This layer maps status **onto** it and
    NEVER redefines it, and NEVER invents a parallel three-valued type or a
    parallel OPEN. ``OPEN`` here is the same first-class escalate verdict
    documented at :mod:`cross_subsumption` (see ``Verdict.OPEN``).
  * :class:`cross_subsumption.DimVerdict` /
    :class:`cross_subsumption.AntecedentVerdict` — the merit verdict of the
    condition a premise-set hangs under, folded in via ``.verdict``.
  * :func:`issue_aggregation.aggregate_issues` — THE OPEN-dominant strict-AND
    fold. Weakest-link propagation is **not re-derived**: it *is* that fold's
    default unordered rule (any OPEN sub-issue dominates), reused verbatim.

The map is deliberately narrow and honest:

  * **SETTLED** {ASSERTED, INFERRED} → :data:`Verdict.SATISFIED` — the premise is
    available for the rest of the argument to rest on.
  * **UNSETTLED** {PRESUPPOSED, CONTESTED, UNKNOWN} → :data:`Verdict.OPEN` —
    escalate: the premise is not settled enough to rest on, and that must
    propagate, not vanish.

A premise's epistemic status **never** emits ``NOT_SATISFIED``. Status can only
leave a premise settled-available (SATISFIED) or open (OPEN); *falsification on
the merits* — declaring a premise actually false — stays the job of
:func:`cross_subsumption.subsume_across`, never this layer. Settledness and
falsity are different questions and are kept different.

The premise type is :class:`case.Fact` (an evidenced factual premise) or
:class:`case.Ground` (an anchored norm-span). **Neither carries a status field**,
and this layer does not add one (add-only: it must not modify ``case``). Status
is therefore *injected alongside* the premise through a thin pairing —
:class:`StatusedPremise` — which references a Fact/Ground by identity, or attaches
to a bare premise name when no Fact object is at hand. The honest note is
explicit: the status is asserted by whoever tags the premise; it is not read off
the fact, because the fact does not carry it.

Pure stdlib. No governance, no corpus, no domain: this module imports neither
``loomground_legal`` nor ``loomground_versum``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence, Tuple

from . import case
from .cross_subsumption import DimVerdict, Verdict
from .issue_aggregation import IssueAggregate, VerdictLike, aggregate_issues


# ── the epistemic status lattice ────────────────────────────────────────────────

class EpistemicStatus(str, Enum):
    """How *settled* a premise is — orthogonal to whether it is true on the
    merits.

    Two settled statuses (a premise the argument may rest on) and three unsettled
    ones (a premise that must escalate):

      * ``ASSERTED``   — stated outright, with a source; settled.
      * ``INFERRED``   — derived from other settled premises; settled.
      * ``PRESUPPOSED``— assumed by the argument but never established; unsettled.
      * ``CONTESTED``  — actively disputed between the parties; unsettled.
      * ``UNKNOWN``    — no position taken, nothing established; unsettled.

    This is *not* a verdict type. It maps onto the existing
    :class:`cross_subsumption.Verdict` via :func:`status_to_verdict`; it never
    stands in for one.
    """

    ASSERTED = "asserted"
    INFERRED = "inferred"
    PRESUPPOSED = "presupposed"
    CONTESTED = "contested"
    UNKNOWN = "unknown"


#: The settled half of the lattice — a premise available to rest on.
SETTLED: frozenset = frozenset({EpistemicStatus.ASSERTED, EpistemicStatus.INFERRED})

#: The unsettled half — a premise that must escalate (→ OPEN), never silently
#: pass.
UNSETTLED: frozenset = frozenset(
    {EpistemicStatus.PRESUPPOSED, EpistemicStatus.CONTESTED, EpistemicStatus.UNKNOWN}
)


# ── classifier ──────────────────────────────────────────────────────────────────

def is_settled(status: EpistemicStatus) -> bool:
    """True iff ``status`` is a settled status (ASSERTED / INFERRED) — a premise
    the rest of the argument may rest on."""
    return EpistemicStatus(status) in SETTLED


def is_unsettled(status: EpistemicStatus) -> bool:
    """True iff ``status`` is an unsettled status (PRESUPPOSED / CONTESTED /
    UNKNOWN) — a premise that must escalate to OPEN, never silently pass."""
    return EpistemicStatus(status) in UNSETTLED


# ── the map onto the existing OPEN vocabulary ───────────────────────────────────

def status_to_verdict(status: EpistemicStatus) -> Verdict:
    """Map an :class:`EpistemicStatus` onto the *existing*
    :class:`cross_subsumption.Verdict`.

      * SETTLED {ASSERTED, INFERRED} → :data:`Verdict.SATISFIED` (available to
        rest on);
      * UNSETTLED {PRESUPPOSED, CONTESTED, UNKNOWN} → :data:`Verdict.OPEN`
        (escalate).

    A status **never** maps to :data:`Verdict.NOT_SATISFIED`: settledness can only
    leave a premise available or open. Declaring a premise actually false is
    falsification on the merits — the job of
    :func:`cross_subsumption.subsume_across`, not of this layer. No new verdict is
    minted here; the return is always one of the three existing ``Verdict``
    members.
    """
    return Verdict.SATISFIED if is_settled(status) else Verdict.OPEN


# ── the thin pairing (status injected ALONGSIDE a premise) ──────────────────────

@dataclass(frozen=True)
class StatusedPremise:
    """A premise paired with its (injected) epistemic status.

    ``status`` is asserted by whoever tags the premise — it is **not** read off
    the fact, because :class:`case.Fact` / :class:`case.Ground` carry no status
    field and this layer must not add one. ``fact`` optionally references the
    Fact/Ground *by identity* (never mutated, never required): status can attach
    to a bare ``name`` alone.

    ``name`` is the sub-issue key this premise contributes under; it must be
    stable, since it is the label carried through
    :func:`issue_aggregation.aggregate_issues`.
    """

    name: str
    status: EpistemicStatus
    fact: Optional[object] = None  # case.Fact | case.Ground | None — by identity
    #: Names of the premises this one rests on. Declared by whoever tags the
    #: premise, exactly like ``status`` — it is not inferred. Empty by default,
    #: so every existing caller is unaffected; it is read only by
    #: :func:`root_causes`, never by the folds.
    depends_on: Tuple[str, ...] = ()

    def to_verdict_item(self) -> Tuple[str, Verdict]:
        """The ``(name, Verdict)`` tuple this premise contributes to the fold.

        The value is a bare :class:`cross_subsumption.Verdict`, which
        :func:`issue_aggregation.aggregate_issues` accepts directly (its coercion
        handles a bare ``Verdict`` via the ``isinstance(v, Verdict)`` branch — no
        reliance on any private symbol)."""
        return (self.name, status_to_verdict(self.status))


# ── weakest-link propagation (REUSES the OPEN-dominant fold) ─────────────────────

def propagate_premises(premises: Iterable[StatusedPremise]) -> IssueAggregate:
    """Weakest-link fold across a set of premises — reusing, not re-deriving, the
    OPEN-dominant aggregation.

    Each premise's status is mapped to a :class:`cross_subsumption.Verdict` and
    handed as a ``(name, Verdict)`` sub-issue to
    :func:`issue_aggregation.aggregate_issues`. Its default unordered rule — *any*
    OPEN sub-issue makes the whole OPEN, dominating even a NOT_SATISFIED sibling —
    delivers weakest-link directly: **one** UNSETTLED premise (→ OPEN) makes the
    whole set OPEN, so a derivation can never come out SATISFIED while resting on
    an unsettled premise. No aggregation is re-implemented here.

    An empty premise set folds to vacuously SATISFIED (the fold's own base case).
    """
    items = [p.to_verdict_item() for p in premises]
    return aggregate_issues(items)


def propagate_under_condition(
    condition_label: str,
    condition_verdict: VerdictLike,
    premises: Iterable[StatusedPremise],
) -> IssueAggregate:
    """Bind a premise-set to the *merit* verdict of the condition it hangs under,
    in one OPEN-dominant fold.

    The condition's own merit verdict (a :class:`cross_subsumption.DimVerdict` /
    :class:`cross_subsumption.AntecedentVerdict`, or a bare
    :class:`cross_subsumption.Verdict`) is folded together with the premises'
    status-verdicts in a single :func:`issue_aggregation.aggregate_issues` call:

        issues = [(condition_label, condition_verdict)]
               + [(p.name, status_to_verdict(p.status)) for p in premises]

    OPEN-dominance then guarantees the honest outcome: **any** condition resting
    on an UNSETTLED premise resolves to OPEN, never SATISFIED — with zero
    re-implemented aggregation. The condition's ``.satisfied`` / ``.open``
    read-side helpers are exactly what the fold consumes via ``.verdict``.
    """
    items: list[Tuple[str, VerdictLike]] = [(condition_label, condition_verdict)]
    items.extend(p.to_verdict_item() for p in premises)
    return aggregate_issues(items)


def propagate_derivation(
    premises: Iterable[StatusedPremise],
    conclusion_verdict: VerdictLike,
    *,
    premises_label: str = "premises",
    conclusion_label: str = "conclusion",
) -> IssueAggregate:
    """Fold a multi-step derivation: premise status-verdicts first, then that
    result together with the conclusion's *merit* verdict — two OPEN-dominant
    folds, still one function each, no aggregation re-implemented.

    Step 1 folds the premises via :func:`propagate_premises` (weakest-link over
    their statuses). Step 2 passes that result's ``.overall`` — a bare
    :class:`cross_subsumption.Verdict` — together with the conclusion's merit
    verdict into a second :func:`issue_aggregation.aggregate_issues` call.

    Because both folds are OPEN-dominant, one UNSETTLED premise makes the
    premise-fold OPEN, which makes the whole derivation OPEN regardless of the
    conclusion's merit — weakest-link end to end.
    """
    premise_fold = propagate_premises(premises)
    return aggregate_issues(
        [
            (premises_label, premise_fold.overall),
            (conclusion_label, conclusion_verdict),
        ]
    )


# ── root-cause selection (ORDERS the fold; re-derives nothing) ──────────────────

@dataclass(frozen=True)
class RootCauseReport:
    """Which unsettled premises are *causes*, and which are only *consequences*.

    ``overall`` is taken from :func:`propagate_premises` — the same OPEN-dominant
    fold, not a second opinion. Everything else is a partition of the premise
    names by why they are open:

      * ``roots`` — premises unsettled **on their own status**. Settling anything
        else cannot settle these; they are the actual causes.
      * ``derived`` — premises whose own status is settled, that are open only
        because they rest (transitively) on a root. Settling the roots settles
        these, and they are what floods a reader's attention.
      * ``settled`` — premises settled in themselves and resting on nothing open.
      * ``dangling`` — ``(premise, missing_name)`` pairs where a declared
        dependency names no premise in the set. Surfaced, never silently
        dropped: a missing dependency means the set is under-described, and a
        reader must know that before trusting the partition.
      * ``cyclic`` — premises on a dependency cycle. Reported rather than
        resolved; a cycle in what rests on what is a defect in the tagging, and
        guessing a root inside one would be a fabricated answer.
    """

    overall: Verdict
    roots: Tuple[str, ...] = ()
    derived: Tuple[str, ...] = ()
    settled: Tuple[str, ...] = ()
    dangling: Tuple[Tuple[str, str], ...] = ()
    cyclic: Tuple[str, ...] = ()

    @property
    def open(self) -> bool:
        return self.overall is Verdict.OPEN

    @property
    def compression(self) -> Tuple[int, int]:
        """``(roots, opens)`` — how much smaller the causal set is than the open
        set. ``(1, 51)`` is the characteristic shape: one early assumption, fifty
        consequences."""
        return (len(self.roots), len(self.roots) + len(self.derived))


def root_causes(premises: Iterable[StatusedPremise]) -> RootCauseReport:
    """Separate the unsettled premises that are *causes* from those that are only
    *consequences*, so a reader is shown the root rather than its descendants.

    The characteristic failure of a long derivation is not an implausible step.
    It is an early assumption that propagates: every later step is individually
    defensible, each inherits the assumption's openness, and the defect sits
    upstream of all of them. Reported flat, that is one cause wearing fifty
    faces, and the fold's ``issues`` tuple lists all fifty.

    This adds **no inference and no verdict**. ``overall`` comes from
    :func:`propagate_premises`; this function only *orders* what that fold
    already decided, using the ``depends_on`` each premise declares. A premise is
    a root iff its **own** status is unsettled — settling something else cannot
    settle it. A premise with a settled status that transitively rests on a root
    is derived.

    Honest edges, both surfaced rather than smoothed:

      * a dependency naming no premise in the set is ``dangling`` — the set is
        under-described and the partition is reported alongside that fact;
      * a premise on a dependency cycle is ``cyclic`` and is classified into
        neither ``roots`` nor ``derived``, because picking a root inside a cycle
        would be a guess.
    """
    items = list(premises)
    by_name = {p.name: p for p in items}

    dangling: list[Tuple[str, str]] = []
    for p in items:
        for dep in p.depends_on:
            if dep not in by_name:
                dangling.append((p.name, dep))

    # Cycle detection over the declared dependency edges (iterative colouring, so
    # a deep chain cannot exhaust the stack).
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {p.name: WHITE for p in items}
    on_cycle: set = set()
    for start in list(colour):
        if colour[start] != WHITE:
            continue
        stack = [(start, iter(by_name[start].depends_on))]
        colour[start] = GREY
        path = [start]
        while stack:
            node, it = stack[-1]
            advanced = False
            for dep in it:
                if dep not in by_name:
                    continue
                if colour[dep] is GREY:
                    on_cycle.update(path[path.index(dep):] if dep in path else [dep, node])
                    continue
                if colour[dep] is WHITE:
                    colour[dep] = GREY
                    stack.append((dep, iter(by_name[dep].depends_on)))
                    path.append(dep)
                    advanced = True
                    break
            if not advanced:
                colour[node] = BLACK
                stack.pop()
                if path and path[-1] == node:
                    path.pop()

    def rests_on_open(name: str) -> bool:
        """True iff ``name`` transitively rests on an independently-unsettled
        premise. Visited-set guarded, so a cycle terminates."""
        seen: set = set()
        frontier = list(by_name[name].depends_on)
        while frontier:
            dep = frontier.pop()
            if dep in seen or dep not in by_name:
                continue
            seen.add(dep)
            if is_unsettled(by_name[dep].status):
                return True
            frontier.extend(by_name[dep].depends_on)
        return False

    roots: list[str] = []
    derived: list[str] = []
    settled: list[str] = []
    cyclic: list[str] = []

    for p in items:                      # input order preserved throughout
        if p.name in on_cycle:
            cyclic.append(p.name)
        elif is_unsettled(p.status):
            roots.append(p.name)
        elif rests_on_open(p.name):
            derived.append(p.name)
        else:
            settled.append(p.name)

    return RootCauseReport(
        overall=propagate_premises(items).overall,
        roots=tuple(roots),
        derived=tuple(derived),
        settled=tuple(settled),
        dangling=tuple(dangling),
        cyclic=tuple(cyclic),
    )
