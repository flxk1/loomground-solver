# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Proxies — what a measurement stands for, and whether anyone checked.

Almost every oversight signal is a proxy. Nobody measures "the client was well
served"; they measure response time, or a satisfaction score, or throughput, and
treat the measurement as standing for the thing. That substitution is usually
sound and always defeasible, and an agent optimising against the measurement will
find the cases where it comes apart faster than a reviewer will.

The failure has a shape, and the shape is checkable once the substitution is
written down:

  * ``gamed``       — the metric improved while what it stands for got worse.
    The whole of Goodhart, stated in two readings.
  * ``unchecked``   — the metric moved and nobody measured what it stands for.
    The **common** case, and the one that must never read as success: an
    unchecked proxy is not weak evidence for its goal, it is no evidence at all.
  * ``misleading``  — the metric got worse while the goal improved. Not a finding
    about the run; a finding about the instrument. It says stop reading the run
    off this measurement.
  * ``tracking``    — both moved together. The substitution held, this once.

Two structural things follow, and they are the part a reviewer cannot do by eye.

*Substitutions chain.* A metric stands for a goal that is itself a proxy for
something further. Support along a chain is weakest-link: one unchecked link
makes the whole chain unchecked, however well every other link tracked. This is
where an audit usually goes wrong, because each hop looks fine locally.

*A chain must ground out.* A proxy that stands for itself, or a cycle of them,
never terminates in anything measured. :func:`chain` refuses both rather than
returning a path, because a substitution that grounds in nothing is not a weak
justification — it is the absence of one.

**Whether a reading improved or worsened is a judgement, and it arrives already
made.** So does the claim that this metric stands for that goal. The kernel holds
no metrics and no goals; it compares declared movements across declared
substitutions and reads none of the names.

Pure stdlib. No governance, no corpus, no domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Mapping, Sequence, Tuple

from .cross_subsumption import Verdict
from .issue_aggregation import IssueAggregate, aggregate_issues

__all__ = [
    "Movement", "Proxy", "Substitution", "KINDS",
    "check_proxies", "chain", "fold_substitutions", "ProxyCycle",
]

#: Substitution outcomes, most-consequential first.
KINDS = ("gamed", "misleading", "unchecked", "tracking")


class ProxyCycle(ValueError):
    """A chain of substitutions that never grounds out in a measured thing."""


class Movement(str, Enum):
    """Which way a reading went. Asserted by whoever took it, never inferred."""

    IMPROVED = "improved"
    UNCHANGED = "unchanged"
    WORSENED = "worsened"
    #: Nobody took this reading. Distinct from ``UNCHANGED`` — see module docs.
    UNMEASURED = "unmeasured"


@dataclass(frozen=True)
class Proxy:
    """A declared substitution: ``metric`` is being read as standing for ``stands_for``.

    ``ref`` should point at where the substitution was decided, because that is
    the thing a reviewer will want to argue with — not the readings, which are
    usually fine, but the claim that this measurement stands for that goal.
    """

    metric: str
    stands_for: str
    ref: str = ""

    def to_dict(self) -> dict:
        out = {"metric": self.metric, "stands_for": self.stands_for}
        if self.ref:
            out["ref"] = self.ref
        return out


@dataclass(frozen=True)
class Substitution:
    """How one declared substitution held up against the two readings."""

    kind: str
    metric: str
    stands_for: str
    why: str

    @property
    def ref(self) -> str:
        """Shaped for :func:`oversight.oversight_brief`, which reads ``ref``/``why``."""
        return self.metric

    def to_dict(self) -> dict:
        return {"kind": self.kind, "metric": self.metric,
                "stands_for": self.stands_for, "why": self.why}


def _movement(readings: Mapping[str, "Movement | str"], subject: str) -> Movement:
    got = readings.get(subject)
    return Movement.UNMEASURED if got is None else Movement(got)


def check_proxies(
    proxies: Iterable[Proxy],
    readings: Mapping[str, "Movement | str"],
) -> Tuple[Substitution, ...]:
    """Compare each declared substitution against the readings. Reports; decides nothing.

    A subject absent from ``readings`` is ``UNMEASURED``, which is deliberately
    not the same as ``UNCHANGED``. "Nobody looked" and "we looked and it held
    still" are different situations, and reading the first as the second is how an
    unchecked proxy comes to be recorded as a healthy one.

    Ordering is by kind (most consequential first), then by metric, so the same
    inputs always report the same way.
    """
    out: list[Substitution] = []
    for proxy in proxies:
        metric = _movement(readings, proxy.metric)
        goal = _movement(readings, proxy.stands_for)
        where = f" ({proxy.ref})" if proxy.ref else ""

        if metric is Movement.UNMEASURED or goal is Movement.UNMEASURED:
            unread = proxy.stands_for if goal is Movement.UNMEASURED else proxy.metric
            out.append(Substitution(
                "unchecked", proxy.metric, proxy.stands_for,
                f"{unread} was not measured, so this reading is no evidence "
                f"about {proxy.stands_for}{where}"))
        elif metric is Movement.IMPROVED and goal is Movement.WORSENED:
            out.append(Substitution(
                "gamed", proxy.metric, proxy.stands_for,
                f"{proxy.metric} improved while {proxy.stands_for}, which it is "
                f"declared to stand for, got worse{where}"))
        elif metric is Movement.WORSENED and goal is Movement.IMPROVED:
            out.append(Substitution(
                "misleading", proxy.metric, proxy.stands_for,
                f"{proxy.metric} got worse while {proxy.stands_for} improved; the "
                f"substitution itself is what is in question{where}"))
        else:
            out.append(Substitution(
                "tracking", proxy.metric, proxy.stands_for,
                f"{proxy.metric} and {proxy.stands_for} moved together{where}"))

    order = {k: n for n, k in enumerate(KINDS)}
    out.sort(key=lambda s: (order.get(s.kind, len(order)), s.metric))
    return tuple(out)


def chain(metric: str, proxies: Iterable[Proxy]) -> Tuple[Proxy, ...]:
    """Follow the substitutions from ``metric`` to whatever finally grounds them.

    Returns the hops in order, empty when ``metric`` stands for nothing declared.
    Raises :class:`ProxyCycle` on a substitution that loops — including a metric
    declared to stand for itself. A cycle is refused rather than truncated,
    because a chain that never terminates in something measured directly is not a
    weak justification but the absence of one, and silently returning the prefix
    would present it as the former.
    """
    edges: Dict[str, Proxy] = {}
    for proxy in proxies:
        edges.setdefault(proxy.metric, proxy)

    path: list[Proxy] = []
    seen = {str(metric)}
    here = str(metric)
    while here in edges:
        hop = edges[here]
        if hop.stands_for in seen:
            raise ProxyCycle(
                f"{hop.metric} stands for {hop.stands_for}, which is already in "
                f"the chain; nothing in it grounds out in a measured thing")
        path.append(hop)
        seen.add(hop.stands_for)
        here = hop.stands_for
    return tuple(path)


def fold_substitutions(substitutions: Sequence[Substitution]) -> IssueAggregate:
    """Fold onto the existing honesty verdict — weakest-link, no new vocabulary.

    ``gamed`` is a **finding**: two readings were compared and the substitution
    was found to have come apart, so it maps to ``NOT_SATISFIED``. ``unchecked``
    and ``misleading`` are open questions — in the first nobody looked, in the
    second the instrument rather than the run is in doubt — so both map to
    ``OPEN`` and, under the OPEN-dominant fold, dominate.

    That dominance is the point when this is applied along a :func:`chain`: one
    unchecked link makes the whole chain unchecked however well every other link
    tracked. An audit that stops at the first hop will not see it.

    No substitutions folds to the aggregation's vacuous ``SATISFIED``, which means
    *nothing was declared*, not that nothing was substituted. Proxies that were
    never written down cannot be checked by anything here.
    """
    return aggregate_issues([
        (f"{s.kind}:{s.metric}",
         Verdict.SATISFIED if s.kind == "tracking"
         else Verdict.NOT_SATISFIED if s.kind == "gamed"
         else Verdict.OPEN)
        for s in substitutions
    ])
