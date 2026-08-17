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
named. "Autonomy 0.34" cannot be acted on; "capped at CONFIRM by reversibility"
can — it says what would have to change.

*Fail-closed.* A factor nobody assessed caps at the floor. Not knowing how
uncertain a situation is is not the same as it being certain, and an unassessed
factor that silently dropped out of the minimum would read as an unconstrained
one. This is the difference between the calculus being conservative and the
calculus being decorative.

**The ceilings are the caller's policy.** This module ships the ladder and the
fold; which factor caps where is a judgement about a deployment, and the kernel
holds no deployments. A table saying "high risk → CONFIRM" is a policy claim and
belongs to whoever can be held to it. Consequently no factor is named here.

**The calculus only ever lowers.** :func:`ceiling` cannot return more than was
delegated, and it cannot return more than the factors permit. Autonomy is restored
by :func:`relax`, which requires a reference to the authorisation for restoring
it — an escalation is a mechanical consequence of the state of the world, but a
de-escalation is an act, and someone is answerable for it.

Pure stdlib. No governance, no corpus, no domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Optional, Sequence, Tuple

from .cross_subsumption import Verdict
from .issue_aggregation import IssueAggregate, aggregate_issues

__all__ = [
    "Autonomy", "FLOOR", "Factor", "Escalation",
    "ceiling", "autonomy_verdict", "fold_autonomy", "relax",
]


class Autonomy(IntEnum):
    """How far an actor may proceed on its own. Ascending.

    ``IntEnum`` because the ordering is the content: the whole calculus is a
    minimum over this ladder, and a set of unordered labels could not express it.

    The two middle rungs are genuinely distinct and are routinely conflated.
    ``CONFIRM`` needs positive assent before the act; ``NOTIFY`` needs only the
    absence of an objection within a window the caller sets. The second is far
    weaker oversight and should not be recorded as the first.
    """

    #: Does not act. The rung an unassessed factor caps at.
    SUSPENDED = 0
    #: May propose; someone else executes.
    PROPOSE = 1
    #: May act once this act has been positively approved.
    CONFIRM = 2
    #: May act after announcing it, unless stopped within the window.
    NOTIFY = 3
    #: May act, and report afterwards.
    ACT = 4


#: The most restrictive rung. Where the calculus lands when it is told nothing.
FLOOR = Autonomy.SUSPENDED


@dataclass(frozen=True)
class Factor:
    """One consideration and the highest autonomy it permits.

    ``ceiling`` of ``None`` means **unassessed**, which is not the same as
    unconstraining: it caps at :data:`FLOOR`. ``why`` should say what was observed
    and, ideally, what would have to change — it is the part a supervisor reads.
    """

    name: str
    ceiling: Optional[Autonomy] = None
    why: str = ""

    @property
    def assessed(self) -> bool:
        return self.ceiling is not None

    @property
    def effective(self) -> Autonomy:
        """The ceiling this factor actually imposes; ``FLOOR`` when unassessed."""
        return FLOOR if self.ceiling is None else Autonomy(self.ceiling)

    def to_dict(self) -> dict:
        out: dict = {"name": self.name, "ceiling": None if self.ceiling is None
                     else Autonomy(self.ceiling).name}
        if self.why:
            out["why"] = self.why
        return out


@dataclass(frozen=True)
class Escalation:
    """What the actor may do, and which factor is the reason it may not do more."""

    granted: Autonomy
    binding: Tuple[str, ...]
    delegated: Autonomy
    factors: Tuple[Factor, ...] = ()

    @property
    def unassessed(self) -> Tuple[str, ...]:
        """Factors nobody assessed. Each is capping at the floor, fail-closed."""
        return tuple(f.name for f in self.factors if not f.assessed)

    def why(self) -> str:
        """One line a supervisor can act on: the rung, and what is holding it."""
        if not self.binding:
            return f"{self.granted.name}: nothing further constrains it"
        return f"{self.granted.name}: capped by {', '.join(self.binding)}"

    def to_dict(self) -> dict:
        return {
            "granted": self.granted.name,
            "delegated": self.delegated.name,
            "binding": list(self.binding),
            "unassessed": list(self.unassessed),
            "factors": [f.to_dict() for f in self.factors],
        }


def ceiling(
    factors: Iterable[Factor], *, delegated: Autonomy
) -> Escalation:
    """The autonomy the factors leave, never above what was ``delegated``.

    ``delegated`` is required rather than defaulted. A default would have to be
    either the top rung — which grants by omission, the failure mode this module
    exists to avoid — or the floor, which would make the common call useless. What
    was actually conferred is known to the caller, so the caller says it.

    ``binding`` names every factor sitting at the granted level, so a reader can
    see what would have to change. When the delegation itself is the constraint
    ``binding`` is empty and ``granted == delegated``: the situation permits more
    than the actor was given, which is a different fact and reads differently.
    """
    factors = tuple(factors)
    delegated = Autonomy(delegated)
    granted = delegated
    for factor in factors:
        granted = min(granted, factor.effective)
    binding = tuple(f.name for f in factors if f.effective == granted
                    and granted < delegated)
    return Escalation(granted=granted, binding=binding,
                      delegated=delegated, factors=factors)


def autonomy_verdict(requested: Autonomy, escalation: Escalation) -> Verdict:
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
    if Autonomy(requested) > escalation.granted:
        return Verdict.NOT_SATISFIED
    return Verdict.OPEN if escalation.unassessed else Verdict.SATISFIED


def fold_autonomy(
    steps: Sequence[Tuple[str, Autonomy, Escalation]]
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


def relax(target: Autonomy, escalation: Escalation, *, authorised_by: str) -> Autonomy:
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
    return min(Autonomy(target), escalation.granted)
