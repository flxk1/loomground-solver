# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Falsifiability — rank oversight evidence by how it could be shown wrong.

Plans, tool calls, outcomes, reported reasoning and independent verification are
routinely treated as evidence of the same kind. They are not, and the ordering
that matters is not how *convincing* each is but how each could be **falsified**:

    replayable derivation  >  span-grounded claim  >  independently verified
    outcome  >  observed tool call  >  declared plan  >  self-reported reasoning

A replayable derivation can be re-derived and found wrong. A span-grounded claim
can be checked against the source. An outcome can be tested. A tool call was
observed. A plan at least states what was intended.

**Self-reported reasoning sits last on principle, not on suspicion.** It is a
claim about a private mechanism, and no procedure can show it false: if the report
is unfaithful to whatever actually produced the behaviour, nothing in the report
reveals that. This is the same objection applied elsewhere in this family to a
system-minted claim about private human conduct, and it holds symmetrically for
agents. A self-report may inform a decision; it may never be the **sole** basis
for one, and this module makes that mechanical rather than aspirational.

The rank maps onto the *existing* honesty verdict — it mints no vocabulary:

  * support at or above the floor  → :data:`cross_subsumption.Verdict.SATISFIED`
  * support below it               → :data:`cross_subsumption.Verdict.OPEN`

A rank **never** emits ``NOT_SATISFIED``, exactly as an epistemic status never
does (:mod:`epistemic_status`). How a claim could be falsified is orthogonal to
whether it is true: weak support means *escalate*, not *false*. Declaring a claim
actually false stays the job of the layer that decides on the merits.

Pure stdlib. No governance, no corpus, no domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Optional, Sequence, Tuple

from .cross_subsumption import Verdict
from .issue_aggregation import IssueAggregate, aggregate_issues

__all__ = [
    "Falsifiability", "SUPPORT_FLOOR", "Evidence",
    "rank", "best_support", "support_verdict", "fold_support",
]


class Falsifiability(IntEnum):
    """How a piece of evidence could be shown wrong. Ascending in strength.

    ``IntEnum`` because the whole point is that these compare; the ordering is
    the content, not an implementation detail.
    """

    #: A claim about a private mechanism. No procedure shows it false.
    SELF_REPORT = 0
    #: States an intention. Checkable against what followed, weakly.
    DECLARED_PLAN = 1
    #: It happened, and was observed happening.
    OBSERVED_TOOL_CALL = 2
    #: An outcome someone other than the actor tested.
    VERIFIED_OUTCOME = 3
    #: Anchored to an exact span of an exact source; anyone holding it can check.
    SPAN_GROUNDED = 4
    #: Re-derivable, and therefore refutable by re-derivation.
    REPLAYABLE = 5


#: The weakest support a conclusion may rest on **alone**. Set one step above
#: ``SELF_REPORT``: the minimum rule that implements "a self-report is never the
#: sole basis". A deployment may raise it; lowering it below this would license
#: exactly what the ordering exists to prevent.
SUPPORT_FLOOR = Falsifiability.DECLARED_PLAN


@dataclass(frozen=True)
class Evidence:
    """A piece of support for a conclusion, with how it could be falsified.

    ``ref`` names the evidence so a reader can go and look at it. The rank is
    asserted by whoever supplies the evidence — this layer does not infer it from
    content, because inferring "this looks span-grounded" is precisely the kind of
    guess the ordering exists to prevent.
    """

    ref: str
    falsifiability: Falsifiability

    def to_dict(self) -> dict:
        return {"ref": self.ref, "falsifiability": self.falsifiability.name}


def rank(evidence: "Evidence | Falsifiability | str") -> Falsifiability:
    """The falsifiability of one piece of evidence, by object, member or name."""
    if isinstance(evidence, Evidence):
        return evidence.falsifiability
    if isinstance(evidence, Falsifiability):
        return evidence
    return Falsifiability[str(evidence).upper()]


def best_support(evidence: Iterable["Evidence | Falsifiability | str"]) -> Optional[Falsifiability]:
    """The strongest support available, or ``None`` when there is none.

    Strongest, not weakest: one replayable derivation is not weakened by sitting
    beside a self-report. Weakest-link applies **across the separate claims** a
    conclusion needs (see :func:`fold_support`), not across the several supports
    for one claim.
    """
    ranks = [rank(e) for e in evidence]
    return max(ranks) if ranks else None


def support_verdict(
    evidence: Iterable["Evidence | Falsifiability | str"],
    *,
    floor: Falsifiability = SUPPORT_FLOOR,
) -> Verdict:
    """Map the support for one claim onto the existing honesty verdict.

    At or above ``floor`` → ``SATISFIED``; below it, or absent entirely → ``OPEN``.
    Never ``NOT_SATISFIED``: weak support escalates, it does not falsify.
    """
    have = best_support(evidence)
    if have is None:
        return Verdict.OPEN
    return Verdict.SATISFIED if have >= floor else Verdict.OPEN


def fold_support(
    claims: Sequence[Tuple[str, Iterable["Evidence | Falsifiability | str"]]],
    *,
    floor: Falsifiability = SUPPORT_FLOOR,
) -> IssueAggregate:
    """Weakest-link across the claims a conclusion rests on.

    Each ``(name, evidence)`` contributes its :func:`support_verdict` as a
    sub-issue to :func:`issue_aggregation.aggregate_issues`, whose OPEN-dominant
    rule is reused verbatim — no aggregation is re-implemented here. One claim
    supported only by a self-report therefore makes the whole thing OPEN, however
    well-evidenced its siblings are, which is the intended result: a conclusion is
    no better supported than its worst-supported step.
    """
    return aggregate_issues(
        [(name, support_verdict(ev, floor=floor)) for name, ev in claims])
