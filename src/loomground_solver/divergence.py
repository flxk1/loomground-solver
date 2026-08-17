# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Divergence — a trajectory compared against the purpose it was given.

The characteristic agentic failure is not an implausible action. It is a sequence
of locally reasonable actions that is globally wrong: every step defensible, every
step logged, and the run as a whole serving something other than what it was
authorised to serve. No amount of reading the steps reveals it, because nothing is
wrong with any of them individually. What is wrong is the *relation* between the
run and its purpose.

**Both terms of that relation must be grounded, or the comparison is worth
nothing.** A purpose asserted at runtime cannot be checked by a supervisor or
reconstructed by a later reviewer; a purpose anchored to the document that
conferred it can be checked by anyone holding the document. So a :class:`Mandate`
cannot be constructed without an :class:`~interop.EvidenceRef`, a step cannot
either, and :func:`detect` requires an :class:`~ports.EvidenceProvider` and
actually calls ``verify`` on both. A finding that rests on a reference nobody
resolved is an assertion wearing the costume of a check, and this module reports
that state rather than producing one.

Four shapes, which are different situations and stay distinguishable:

  * ``ungrounded``      — a reference did not verify. Not a claim about the run;
    a claim about the record of it. It escalates.
  * ``out-of-mandate``  — a step serves no purpose the mandate declares. The run
    did something it was not authorised to do.
  * ``defeats-purpose`` — a step works **against** a purpose the mandate declares.
    This is the letter-versus-spirit case: the instruction may be satisfied to the
    word while the reason for it is defeated.
  * ``unserved``        — the mandate declares a purpose no step served. Weaker
    than the others: a run may simply be unfinished, so it escalates rather than
    reporting a failure.

An unverifiable **mandate** stops the comparison outright, because it is the
second term of every comparison this module makes; findings against a frame nobody
can check would read as authoritative and would not be. An unverifiable **step**
costs only itself: it is reported, and dropped from the comparison and from the
record of what the run served.

**What the kernel contributes is the comparison, not the judgement.** Whether a
given step serves or defeats a given purpose is a judgement — made by a model, a
rule, or a person — and it arrives already made, on the step. A purpose is not a
kernel concept and must not become one (``test_dependency_inversion``); purposes
here are opaque identifiers the caller supplies and the kernel only ever compares
for membership.

**And the knowledge store is not a dependency.** The mandate and the trajectory
live one layer down, in a knowledge engine that anchors claims to spans and
refuses an ungrounded step. This module reaches them through the port that already
exists for exactly this, so the grounding is real without the substrate being
imported.

Pure stdlib. No governance, no corpus, no domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence, Tuple

from .cross_subsumption import Verdict
from .interop import EvidenceRef
from .issue_aggregation import IssueAggregate, aggregate_issues
from .ports import EvidenceProvider

__all__ = [
    "Mandate", "TrajectoryStep", "Divergence",
    "detect", "fold_divergences", "KINDS",
]

#: Divergence kinds, most-consequential first — the order a reader should meet them.
#: ``ungrounded`` leads because it qualifies everything below it.
KINDS = ("ungrounded", "defeats-purpose", "out-of-mandate", "unserved")


def _cite(ref: EvidenceRef) -> str:
    """A readable pointer to the evidence, for the reason a supervisor reads."""
    out = ref.source_id or "?"
    if ref.item_id:
        out += f"#{ref.item_id}"
    if ref.span_start is not None and ref.span_end is not None:
        out += f":{ref.span_start}-{ref.span_end}"
    return out


@dataclass(frozen=True)
class Mandate:
    """The purposes an actor was authorised to pursue, and the span they were read from.

    ``evidence`` is required and has no default. A mandate that cannot say where it
    came from is the thing this module exists to refuse — the comparison it frames
    would be only as good as the assertion, which is what an oversight surface must
    never quietly become. ``purposes`` are opaque to the kernel: it compares them
    and reads none of them.
    """

    evidence: EvidenceRef
    purposes: frozenset = field(default_factory=frozenset)

    @property
    def ref(self) -> str:
        """The citation, so a reader can go and check what was actually conferred."""
        return _cite(self.evidence)


@dataclass(frozen=True)
class TrajectoryStep:
    """One step: what it was, where the record of it is, and what it serves or defeats.

    ``ref`` names the action and ``evidence`` grounds it having happened — the same
    split a process composition makes between a participant's target and the
    evidence supporting it, and for the same reason: a narrative about what an
    agent did, unattached to the record of it doing so, is unfalsifiable.

    The kernel does not derive ``serves`` or ``defeats``. Inferring which purpose
    an action served would be exactly the guess this layer exists to make
    checkable, and the guess belongs to whoever can be held to it.
    """

    ref: str
    evidence: EvidenceRef
    serves: frozenset = field(default_factory=frozenset)
    defeats: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class Divergence:
    """One way a run departed from its purpose, or one reason it cannot be checked.

    ``ref`` and ``why`` are shaped for :func:`oversight.oversight_brief`, which
    accepts either these objects or ``(ref, why)`` pairs.
    """

    kind: str
    ref: str
    why: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "ref": self.ref, "why": self.why}


def _verifies(evidence: EvidenceProvider, ref: EvidenceRef) -> bool:
    """Verify, treating a provider that raises as a failure to verify.

    A store that cannot answer has not confirmed anything, and reading an
    exception as a pass would put the fail-open case exactly where it does the
    most damage.
    """
    try:
        return bool(evidence.verify(ref))
    except Exception:
        return False


def detect(
    mandate: Mandate,
    steps: Iterable[TrajectoryStep],
    *,
    evidence: EvidenceProvider,
) -> Tuple[Divergence, ...]:
    """Compare a grounded trajectory against its grounded mandate. Reports; resolves nothing.

    ``evidence`` is required and keyword-only. There is no permissive default and
    no in-package no-op provider: a caller who wants findings without verification
    must write the provider that returns ``True``, and thereby say so. That is the
    difference between a check and an assertion, and it should cost a line of
    someone's code rather than nothing at all.

    An empty mandate is **not** treated as permission for everything: an actor
    given no purpose has been given nothing to pursue, so every step is
    out-of-mandate. That is the same reading the delegation rules take of an
    unmandated delegator, and the fail-closed one.

    Ordering is by kind (most consequential first), then by reference, so the same
    run always reports the same way.
    """
    steps = list(steps)
    out: list[Divergence] = []

    if not _verifies(evidence, mandate.evidence):
        return (Divergence(
            "ungrounded", mandate.ref,
            "the mandate's evidence did not verify, so there is no checkable "
            "purpose to compare the run against"),)

    grounded: list[TrajectoryStep] = []
    for step in steps:
        if _verifies(evidence, step.evidence):
            grounded.append(step)
        else:
            out.append(Divergence(
                "ungrounded", step.ref,
                f"the record of this step did not verify ({_cite(step.evidence)}); "
                f"it is excluded from the comparison"))

    declared = frozenset(mandate.purposes)

    for step in grounded:
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

    served = (frozenset().union(*(frozenset(s.serves) for s in grounded))
              if grounded else frozenset())
    for purpose in sorted(declared - served):
        out.append(Divergence(
            "unserved", purpose,
            "declared in the mandate; no step whose record verified served it"))

    order = {k: n for n, k in enumerate(KINDS)}
    out.sort(key=lambda d: (order.get(d.kind, len(order)), d.ref))
    return tuple(out)


def fold_divergences(divergences: Sequence[Divergence]) -> IssueAggregate:
    """Fold divergences into the existing honesty verdict — no new vocabulary.

    ``defeats-purpose`` and ``out-of-mandate`` are **findings**: something was
    compared and found wrong, so they map to ``NOT_SATISFIED``. ``unserved`` and
    ``ungrounded`` are open questions — a run may be unfinished, and a reference
    that did not resolve says nothing about conduct — so they map to ``OPEN`` and,
    under the OPEN-dominant fold, dominate. That is the honest priority: "we
    cannot check this" and "we do not yet know whether this purpose was served"
    should not be closed by having found a different failure.

    No divergences folds to the aggregation's vacuous ``SATISFIED``. That means
    *nothing was found*, which is not the same as the run being right — the
    comparison is only as good as the judgements handed in.
    """
    return aggregate_issues([
        (f"{d.kind}:{d.ref}",
         Verdict.NOT_SATISFIED
         if d.kind in ("defeats-purpose", "out-of-mandate") else Verdict.OPEN)
        for d in divergences
    ])
