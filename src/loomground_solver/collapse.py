# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Conjunctive collapse — a decomposition where any one term at its floor
collapses the whole, folded through the aggregation that already exists.

Some properties decompose into constituents that multiply rather than add. The
worked example is oversight: observability, intervenability, comprehensibility,
authority and timeliness. A supervisor who can see everything, understand it, and
is entitled to act, but who is told **after** the effect, has no control at all —
one term at its floor takes the product to zero however healthy the others are.
Oversight is then formally present and functionally absent, which is the
distinction worth being able to state.

Written as a product this looks like arithmetic. It is not, and treating it as
arithmetic is the trap: multiplying scores invents a magnitude nobody measured
and lets a strong term visibly compensate for a weak one, which is exactly what a
collapsing conjunction must not permit. The honest reading is **weakest-link over
a conjunction**, and this kernel already has that: the OPEN-dominant strict-AND
fold in :mod:`issue_aggregation`. This module reuses it and computes no product.

**The constituents are the caller's.** This module names none of them. A
decomposition is a claim about a subject area, and the kernel holds no subject
areas; a consumer supplies the names and which of them is at its floor.

Three states, and the third is the one usually lost:

  * ``PRESENT``    — above its floor → ``SATISFIED``
  * ``AT_FLOOR``   — measured, and at its lowest level → ``NOT_SATISFIED``
  * ``UNASSIGNED`` — nobody measured it → ``OPEN``

A measured zero is a **finding**; an unmeasured constituent is an **open
question**. Collapsing them into one value would report "we know this is broken"
and "nobody looked" identically, and those call for different actions. Because
the reused fold is OPEN-dominant, an unmeasured constituent dominates a measured
failure elsewhere — correctly, since repairing the failure must not close a
question nobody has yet asked.

Pure stdlib. No governance, no corpus, no domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Tuple

from .cross_subsumption import Verdict
from .issue_aggregation import IssueAggregate, aggregate_issues

__all__ = ["ConstituentState", "Constituent", "state_to_verdict", "collapse"]


class ConstituentState(str, Enum):
    """Where one constituent of a collapsing conjunction stands."""

    #: Above its floor — this constituent is not what is holding the whole back.
    PRESENT = "present"
    #: Measured, and at its lowest level. The conjunction collapses here.
    AT_FLOOR = "at_floor"
    #: Nobody assigned it. Not a floor, and not a pass.
    UNASSIGNED = "unassigned"


@dataclass(frozen=True)
class Constituent:
    """One named term of the conjunction, and where it stands.

    ``name`` is the caller's; this module ships no vocabulary. ``note`` optionally
    records how the state was established, which matters most for a constituent
    that cannot be read off a system at all and must be measured against people.
    """

    name: str
    state: ConstituentState
    note: str = ""

    def to_dict(self) -> dict:
        out = {"name": self.name, "state": self.state.value}
        if self.note:
            out["note"] = self.note
        return out


def state_to_verdict(state: ConstituentState) -> Verdict:
    """Map a constituent's state onto the *existing* three-valued verdict.

    No verdict is minted here, and the mapping is deliberately not two-valued: a
    measured floor and an unmeasured constituent are different situations and stay
    different.
    """
    state = ConstituentState(state)
    if state is ConstituentState.PRESENT:
        return Verdict.SATISFIED
    if state is ConstituentState.AT_FLOOR:
        return Verdict.NOT_SATISFIED
    return Verdict.OPEN


def collapse(constituents: Iterable[Constituent]) -> IssueAggregate:
    """Fold a collapsing conjunction — weakest-link, never a product.

    Each constituent contributes ``(name, verdict)`` to
    :func:`issue_aggregation.aggregate_issues`, whose OPEN-dominant strict-AND
    rule delivers the collapse directly: one term at its floor prevents
    ``SATISFIED`` no matter how strong the rest are, and one unmeasured term
    dominates even that.

    The returned aggregate carries every sub-issue, so a reader can see **which**
    constituent collapsed the whole. That is the difference between knowing
    oversight is absent and knowing why, and a bare scalar cannot express it.

    An empty conjunction folds to the aggregation's own vacuous base case; this
    module invents no answer for a decomposition nobody supplied.
    """
    return aggregate_issues(
        [(c.name, state_to_verdict(c.state)) for c in constituents])
