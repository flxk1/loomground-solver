# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Escalation — autonomy as a ceiling several factors impose, not a score.

Autonomy is usually written as a function of risk, uncertainty, reversibility,
context and competence. Written that way it invites a weighted sum, and a
weighted sum is the wrong shape for this: it invents a magnitude nobody measured,
and it lets a strong factor visibly buy back autonomy that a weak one removed.
High competence does not make an irreversible act reversible. A low-risk framing
does not make an unmeasured uncertainty measured.

The honest reading is that **each factor imposes a ceiling, and the actor gets the
lowest one**. That is a minimum over an ordered ladder, and it has the three
properties a weighted sum lacks:

*Monotone.* Worsening any factor can only lower the granted autonomy, never raise
it. Nothing compensates for anything.

*Attributable.* There is always a factor that is doing the capping, and it can be
named. "Autonomy 0.34" cannot be acted on; "capped by reversibility" can — it
says what would have to change.

*Fail-closed.* A factor nobody assessed caps at the floor. Not knowing how
uncertain a situation is is not the same as it being certain, and an unassessed
factor that silently dropped out of the minimum would read as an unconstrained
one. This is the difference between the calculus being conservative and the
calculus being decorative.

**The ladder is the caller's, and so are the ceilings.** This module ships the
comparison and the fold; it ships no levels. That is not fastidiousness — the
governance language already owns this ladder and already publishes it as
remappable data, saying so in as many words: *policy supplies the levels, their
meanings, and their order; the language owns only the comparison rule.* A second
ladder here would be a divergent copy of a thing that already exists, in the layer
that holds no deployments. A host reads its levels from wherever it keeps its
policy and hands them in as a :class:`Ladder`. Which factor caps where is the same
kind of claim, and is likewise the caller's; consequently no factor is named here.

**The calculus only ever lowers.** :func:`ceiling` cannot return more than was
delegated, and it cannot return more than the factors permit. Autonomy is restored
by :func:`relax`, which requires a reference to the authorisation for restoring
it — an escalation is a mechanical consequence of the state of the world, but a
de-escalation is an act, and someone is answerable for it.

Pure stdlib. No governance, no corpus, no domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

from .cross_subsumption import Verdict
from .issue_aggregation import IssueAggregate, aggregate_issues

__all__ = [
    "Ladder", "Factor", "Escalation",
    "ceiling", "autonomy_verdict", "fold_autonomy", "relax",
]


@dataclass(frozen=True)
class Ladder:
    """The ordered autonomy levels a deployment uses, ascending.

    ``levels[0]`` is the floor — the rung an unassessed factor caps at — and
    ``levels[-1]`` is the most latitude the ladder can express. The kernel reads
    none of the names; it compares positions, so any labelling works.

    The ordering is the whole content. A set of unordered labels could not
    express a minimum, and that minimum is the entire calculus.
    """

    levels: Tuple[str, ...]

    def __post_init__(self) -> None:
        levels = tuple(str(level) for level in self.levels)
        if not levels:
            raise ValueError("a ladder needs at least one level")
        if len(set(levels)) != len(levels):
            raise ValueError(f"ladder levels must be distinct: {levels}")
        object.__setattr__(self, "levels", levels)

    @property
    def floor(self) -> str:
        """The most restrictive rung. Where the calculus lands when told nothing."""
        return self.levels[0]

    @property
    def top(self) -> str:
        return self.levels[-1]

    def rank(self, level: str) -> int:
        """Position of ``level``. Raises for a level this ladder does not carry.

        Refused rather than coerced: a level off the ladder is a wiring mistake,
        and quietly reading it as the floor would turn a mistake into a policy.
        """
        try:
            return self.levels.index(str(level))
        except ValueError:
            raise ValueError(
                f"{level!r} is not on this ladder: {self.levels}") from None

    def lower(self, one: str, other: str) -> str:
        """Whichever of the two sits lower. The only operation the fold needs."""
        return one if self.rank(one) <= self.rank(other) else other


@dataclass(frozen=True)
class Factor:
    """One consideration and the highest autonomy it permits.

    ``ceiling`` of ``None`` means **unassessed**, which is not the same as
    unconstraining: it caps at the ladder's floor. ``why`` should say what was
    observed and, ideally, what would have to change — it is the part a supervisor
    reads.
    """

    name: str
    ceiling: Optional[str] = None
    why: str = ""

    @property
    def assessed(self) -> bool:
        return self.ceiling is not None

    def effective(self, ladder: Ladder) -> str:
        """The ceiling this factor imposes on ``ladder``; its floor when unassessed."""
        return ladder.floor if self.ceiling is None else str(self.ceiling)

    def to_dict(self) -> dict:
        out: dict = {"name": self.name, "ceiling": self.ceiling}
        if self.why:
            out["why"] = self.why
        return out


@dataclass(frozen=True)
class Escalation:
    """What the actor may do, and which factor is the reason it may not do more."""

    granted: str
    binding: Tuple[str, ...]
    delegated: str
    ladder: Ladder
    factors: Tuple[Factor, ...] = ()

    @property
    def unassessed(self) -> Tuple[str, ...]:
        """Factors nobody assessed. Each is capping at the floor, fail-closed."""
        return tuple(f.name for f in self.factors if not f.assessed)

    def why(self) -> str:
        """One line a supervisor can act on: the rung, and what is holding it."""
        if not self.binding:
            return f"{self.granted}: nothing further constrains it"
        return f"{self.granted}: capped by {', '.join(self.binding)}"

    def to_dict(self) -> dict:
        return {
            "granted": self.granted,
            "delegated": self.delegated,
            "ladder": list(self.ladder.levels),
            "binding": list(self.binding),
            "unassessed": list(self.unassessed),
            "factors": [f.to_dict() for f in self.factors],
        }


def ceiling(
    factors: Iterable[Factor], *, delegated: str, ladder: Ladder
) -> Escalation:
    """The autonomy the factors leave, never above what was ``delegated``.

    ``delegated`` and ``ladder`` are both required rather than defaulted. A
    default delegation would have to be either the top rung — which grants by
    omission, the failure mode this module exists to avoid — or the floor, which
    would make the common call useless. A default *ladder* would be a set of
    levels this kernel invented for a deployment it knows nothing about.

    ``binding`` names every factor sitting at the granted level, so a reader can
    see what would have to change. When the delegation itself is the constraint
    ``binding`` is empty and ``granted == delegated``: the situation permits more
    than the actor was given, which is a different fact and reads differently.
    """
    factors = tuple(factors)
    granted = str(delegated)
    ladder.rank(granted)                      # a delegation off the ladder is a bug
    for factor in factors:
        granted = ladder.lower(granted, factor.effective(ladder))
    binding = tuple(
        f.name for f in factors
        if f.effective(ladder) == granted and ladder.rank(granted) < ladder.rank(delegated))
    return Escalation(granted=granted, binding=binding, delegated=str(delegated),
                      ladder=ladder, factors=factors)


def autonomy_verdict(requested: str, escalation: Escalation) -> Verdict:
    """Was the autonomy the actor took within what the factors leave it?

    Mapped onto the existing honesty verdict; no vocabulary is minted:

      * above the granted ceiling → ``NOT_SATISFIED``. A finding: something was
        compared and found to exceed its authority.
      * within it, but some factor unassessed → ``OPEN``. The comparison was made
        against a ceiling partly nobody established, so it escalates rather than
        passing. It does **not** become a finding — an unassessed factor is a gap
        in the assessment, not evidence of overreach.
      * within it, everything assessed → ``SATISFIED``.

    An unassessed factor already caps at the floor, so overreach is detected
    whether or not the assessment was complete. The OPEN case is about not
    silently reporting an incomplete assessment as a clean one.
    """
    ladder = escalation.ladder
    if ladder.rank(requested) > ladder.rank(escalation.granted):
        return Verdict.NOT_SATISFIED
    return Verdict.OPEN if escalation.unassessed else Verdict.SATISFIED


def fold_autonomy(
    steps: Sequence[Tuple[str, str, Escalation]]
) -> IssueAggregate:
    """Weakest-link across the steps of a run, through the existing fold.

    Each ``(ref, requested, escalation)`` contributes its
    :func:`autonomy_verdict` as a sub-issue to
    :func:`issue_aggregation.aggregate_issues`. One step taken above its ceiling
    makes the run NOT_SATISFIED however many steps were within theirs; one step
    assessed against an incomplete set of factors dominates even that, which is
    the intended priority — a gap in the assessment is not closed by having found
    a failure somewhere else.
    """
    return aggregate_issues(
        [(ref, autonomy_verdict(requested, esc)) for ref, requested, esc in steps])


def relax(target: str, escalation: Escalation, *, authorised_by: str) -> str:
    """Restore autonomy, up to but never beyond what the factors currently leave.

    Escalation is a mechanical consequence of the state of the world and needs no
    authorisation. Restoring autonomy is an act: someone decided the situation had
    improved enough, and ``authorised_by`` records who, so the decision can be
    found later. An empty reference raises rather than defaulting to anonymous.

    The result is still bounded by ``escalation.granted``, so this can lift an
    actor back toward its ceiling but never through it.
    """
    if not str(authorised_by).strip():
        raise ValueError("relaxing autonomy requires a reference to its authorisation")
    return escalation.ladder.lower(str(target), escalation.granted)
