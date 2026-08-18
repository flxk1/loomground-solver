# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The oversight brief — the bounded object a supervisor actually needs.

A supervisor cannot read every step of a long derivation, and sampling steps
leaves blind spots. The usual response is to ship the trace, and the evidence is
that this makes things worse rather than better: a trace raises a reader's
confidence without improving their detection of errors. It is a sample of output.
It grows with the number of steps, it is uniform in density, and it puts attention
everywhere except where the reasoning was actually unsure.

This module assembles the other object — the places the reasoning **could not
settle** — from what the kernel already computes:

  * :func:`epistemic_status.root_causes` — premises unsettled on their own status,
    each carrying the settled-but-dependent premises it explains;
  * :class:`decision.DecisionSpace` — the ``undecided`` set, the genuine choice
    the space could not close;
  * the ``negative_space`` filter of :mod:`fingerprint` — unfired defeaters,
    untriggered exceptions, reported gaps;
  * divergences, supplied by a caller, because the kernel holds no notion of a
    purpose to diverge from (see the boundary below).

**The claim, and it is falsifiable.** A brief's size is a function of what went
unresolved, not of how many steps were taken. Fifty inferred steps resting on one
unsettled assumption contribute **one** item — the assumption, carrying the fifty
as what it explains — not fifty. A run of a thousand steps that settles cleanly
yields an empty brief. `tests/test_oversight_brief.py` measures exactly this, and
a brief that grew with step count would falsify the claim rather than need tuning.

**This module decides nothing.** It selects and orders what other layers already
determined; it computes no verdict, mints no status, and resolves nothing. If it
ever starts deciding, it has become a second opinion competing with the fold.

**Boundary.** Divergence — a trajectory failing to serve the purpose it was given
— is the item a supervisor most needs, and the kernel cannot derive it: a purpose
is not a kernel concept and must not become one (``test_dependency_inversion``).
Divergences therefore arrive through the caller, already judged. This module
carries them into the brief and does not second-guess them.

Pure stdlib. No governance, no corpus, no domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence, Tuple

from .decision import DecisionSpace
from .epistemic_status import EpistemicStatus, StatusedPremise, root_causes

__all__ = ["BriefItem", "OversightBrief", "oversight_brief"]


#: Ordering of item kinds in a brief, most-consequential first. A reader who stops
#: after the first item should have stopped on the most important one.
KIND_ORDER = (
    "divergence",             # the trajectory did not serve its purpose
    "root-presupposition",    # unsettled on its own status; everything below rests here
    "unresolved-option",      # the space could not close; a choice is genuinely open
    "unfired-defeater",       # a defeater that did not fire — it might have
    "untriggered-exception",  # an exception the chain never reached
    "gap",                    # the reasoning reported a hole in itself
)


@dataclass(frozen=True)
class BriefItem:
    """One thing a supervisor must look at, and why.

    ``why`` states the reason it is unresolved, not merely that it is: an item a
    reader cannot act on is as useless as no item.

    ``explains`` names what this item accounts for — the settled-but-dependent
    premises that are open only because this one is. It is what makes the brief
    compress: fifty consequences of one assumption are carried *here*, as
    context, rather than listed as fifty separate things to read.
    """

    kind: str
    ref: str
    why: str
    explains: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        out = {"kind": self.kind, "ref": self.ref, "why": self.why}
        if self.explains:
            out["explains"] = list(self.explains)
        return out


@dataclass(frozen=True)
class OversightBrief:
    """What could not be settled, ordered so the most consequential is first.

    ``settled_omitted`` counts what resolved cleanly and is therefore absent. It
    is reported because a brief that says nothing is ambiguous between "nothing
    was checked" and "everything checked out", and those are not the same
    situation for a reader.
    """

    items: Tuple[BriefItem, ...] = ()
    settled_omitted: int = 0

    def __len__(self) -> int:
        return len(self.items)

    @property
    def empty(self) -> bool:
        return not self.items

    def of_kind(self, kind: str) -> Tuple[BriefItem, ...]:
        return tuple(i for i in self.items if i.kind == kind)

    def to_dict(self) -> dict:
        return {"items": [i.to_dict() for i in self.items],
                "settled_omitted": self.settled_omitted}


_WHY = {
    EpistemicStatus.PRESUPPOSED: "assumed by the argument, never established",
    EpistemicStatus.CONTESTED: "actively disputed",
    EpistemicStatus.UNKNOWN: "no position taken, nothing established",
}


def oversight_brief(
    *,
    premises: Iterable[StatusedPremise] = (),
    space: Optional[DecisionSpace] = None,
    negative_space: Optional[dict] = None,
    divergences: Sequence[Any] = (),
) -> OversightBrief:
    """Assemble the bounded set of things a supervisor must look at.

    Every argument is optional: a caller with only a decision space gets a brief
    over that alone. Nothing is invented for an absent source.

    ``divergences`` is a sequence of either ``(ref, why)`` pairs or objects with
    ``ref``/``why`` attributes, judged by the caller. They lead the brief, because
    a trajectory that did not serve its purpose is the thing least likely to be
    noticed from the steps themselves.
    """
    items: list[BriefItem] = []
    settled = 0

    for d in divergences:
        ref, why = (d if isinstance(d, tuple)
                    else (getattr(d, "ref", str(d)), getattr(d, "why", "")))
        items.append(BriefItem("divergence", str(ref),
                               str(why) or "trajectory did not serve its purpose"))

    premises = list(premises)
    if premises:
        report = root_causes(premises)
        by_name = {p.name: p for p in premises}
        # Derived premises are carried on the root that explains them, not listed
        # separately: one assumption with fifty consequences is one item.
        for name in report.roots:
            status = by_name[name].status
            items.append(BriefItem(
                "root-presupposition", name,
                _WHY.get(EpistemicStatus(status), "unsettled"),
                explains=report.derived))
        settled += len(report.settled)
        # A cycle cannot be attributed to a root, so it is surfaced as its own gap
        # rather than silently dropped or arbitrarily rooted.
        for name in report.cyclic:
            items.append(BriefItem(
                "gap", name, "on a dependency cycle; no root can be attributed"))
        for premise, missing in report.dangling:
            items.append(BriefItem(
                "gap", premise, f"depends on {missing!r}, which the set does not contain"))

    if space is not None:
        for option in sorted(space.undecided):
            items.append(BriefItem(
                "unresolved-option", str(option),
                "the space could not separate this from its rivals"))
        settled += len(space.accepted)

    ns = negative_space or {}
    for name in sorted(ns.get("unfired_defeaters", []) or []):
        items.append(BriefItem("unfired-defeater", str(name),
                               "declared but did not fire in this derivation"))
    for text in sorted(ns.get("untriggered_exceptions", []) or []):
        items.append(BriefItem("untriggered-exception", str(text),
                               "an exception the chain never reached"))
    for gap in sorted(ns.get("gaps", []) or []):
        items.append(BriefItem("gap", str(gap), "the reasoning reported a hole here"))

    order = {k: n for n, k in enumerate(KIND_ORDER)}
    items.sort(key=lambda i: (order.get(i.kind, len(order)), i.ref))
    return OversightBrief(items=tuple(items), settled_omitted=settled)
