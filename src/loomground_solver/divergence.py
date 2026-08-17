# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Divergence — a trajectory compared against the purpose it was given.

The characteristic agentic failure is not an implausible action. It is a sequence
of locally reasonable actions that is globally wrong: every step defensible, every
step logged, and the run as a whole serving something other than what it was
authorised to serve. No amount of reading the steps reveals it, because nothing is
wrong with any of them individually. What is wrong is the *relation* between the
run and its purpose, and that relation has to be stated somewhere before it can be
checked.

Three shapes, which are different failures and stay distinguishable:

  * ``out-of-mandate``  — a step serves no purpose the mandate declares. The run
    did something it was not authorised to do.
  * ``defeats-purpose`` — a step works **against** a purpose the mandate declares.
    This is the letter-versus-spirit case: the instruction may be satisfied to the
    word while the reason for it is defeated.
  * ``unserved``        — the mandate declares a purpose no step served. Weaker
    than the others: a run may simply be unfinished, so it escalates rather than
    reporting a failure.

**What the kernel contributes is the comparison, not the judgement.** Whether a
given step serves or defeats a given purpose is a judgement — made by a model, a
rule, or a person — and it arrives already made, on the step. A purpose is not a
kernel concept and must not become one (``test_dependency_inversion``); purposes
here are opaque identifiers the caller supplies and the kernel only ever compares
for membership. This module can tell you that the run went outside what it was
given. It cannot tell you what it was given.

The output plugs directly into :func:`oversight.oversight_brief` as its
``divergences`` argument, which is where a supervisor will actually read it.

Pure stdlib. No governance, no corpus, no domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence, Tuple

from .cross_subsumption import Verdict
from .issue_aggregation import IssueAggregate, aggregate_issues

__all__ = [
    "Mandate", "TrajectoryStep", "Divergence",
    "detect", "fold_divergences", "KINDS",
]

#: Divergence kinds, most-consequential first — the order a reader should meet them.
KINDS = ("defeats-purpose", "out-of-mandate", "unserved")


@dataclass(frozen=True)
class Mandate:
    """The purposes an actor was authorised to pursue, and where that is recorded.

    ``ref`` should point at the span the purpose was read from, so a reader can go
    and check what was actually conferred rather than taking this on trust.
    ``purposes`` are opaque to the kernel: it compares them and reads none of them.
    """

    ref: str
    purposes: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class TrajectoryStep:
    """One step, with what it serves and what it defeats — both already judged.

    The kernel does not derive ``serves`` or ``defeats``. Inferring which purpose
    an action served would be exactly the guess this layer exists to make
    checkable, and the guess belongs to whoever can be held to it.
    """

    ref: str
    serves: frozenset = field(default_factory=frozenset)
    defeats: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class Divergence:
    """One way a run departed from its purpose.

    ``ref`` and ``why`` are shaped for :func:`oversight.oversight_brief`, which
    accepts either these objects or ``(ref, why)`` pairs.
    """

    kind: str
    ref: str
    why: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "ref": self.ref, "why": self.why}


def detect(
    mandate: Mandate, steps: Iterable[TrajectoryStep]
) -> Tuple[Divergence, ...]:
    """Compare a trajectory against its mandate. Reports; resolves nothing.

    An empty mandate is **not** treated as permission for everything: an actor
    given no purpose has been given nothing to pursue, so every step is
    out-of-mandate. That is the same reading the delegation rules take of an
    unmandated delegator, and the fail-closed one.

    Ordering is by kind (most consequential first), then by step reference, so
    the same run always reports the same way.
    """
    steps = list(steps)
    declared = frozenset(mandate.purposes)
    out: list[Divergence] = []

    for step in steps:
        defeated = sorted(frozenset(step.defeats) & declared)
        if defeated:
            out.append(Divergence(
                "defeats-purpose", step.ref,
                f"works against {', '.join(defeated)}, which the mandate declares "
                f"({mandate.ref})"))
        if not (frozenset(step.serves) & declared):
            out.append(Divergence(
                "out-of-mandate", step.ref,
                "serves no purpose the mandate declares"
                if declared else
                f"the mandate ({mandate.ref}) declares no purpose, so nothing is authorised"))

    served = frozenset().union(*(frozenset(s.serves) for s in steps)) if steps else frozenset()
    for purpose in sorted(declared - served):
        out.append(Divergence(
            "unserved", purpose,
            "declared in the mandate; no step served it"))

    order = {k: n for n, k in enumerate(KINDS)}
    out.sort(key=lambda d: (order.get(d.kind, len(order)), d.ref))
    return tuple(out)


def fold_divergences(divergences: Sequence[Divergence]) -> IssueAggregate:
    """Fold divergences into the existing honesty verdict — no new vocabulary.

    ``defeats-purpose`` and ``out-of-mandate`` are **findings**: something was
    compared and found wrong, so they map to ``NOT_SATISFIED``. ``unserved`` is an
    open question — a run may be unfinished — so it maps to ``OPEN`` and, under
    the OPEN-dominant fold, dominates. That is the honest priority: "we do not yet
    know whether this purpose was served" should not be closed by having found a
    different failure.

    No divergences folds to the aggregation's vacuous ``SATISFIED``. That means
    *nothing was found*, which is not the same as the run being right — the
    comparison is only as good as the judgements handed in.
    """
    return aggregate_issues([
        (f"{d.kind}:{d.ref}",
         Verdict.OPEN if d.kind == "unserved" else Verdict.NOT_SATISFIED)
        for d in divergences
    ])
