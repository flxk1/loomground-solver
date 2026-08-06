# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Burden of proof — allocation, presumption, standard of proof, and *non-liquet*
(Family L, O102-O105 + O107).

When the facts run out, a decision still has to be made. This module encodes the
machinery that makes that possible without *guessing the fact*:

* **Burden of production** (O102) and **burden of persuasion** (O103) — who must
  bring an element forward, and who loses if it stays unproven.
* **Standard of proof** (O104) — the threshold an element must clear, on an
  ordered scale from *Glaubhaftmachung* to *beyond reasonable doubt*.
* **Rebuttable presumptions** (O105) — a fact supplied by law once its basic
  facts are shown, standing until a rebutting fact defeats it.
* **Non-liquet** (O107) — the decisive move of the family: an element that is
  neither proven nor disproven is **left un-established** and **decided against
  the party who bore the burden of persuasion**. The fact itself is never
  invented; only its allocation is decided.

The whole thing rides on the closed-world *proven* check already in the package:
:func:`loomground_solver.subsumption.holds` (present ⇒ proven; consumed both for
element presence and, applied to :func:`~loomground_solver.subsumption.neg` of a
literal, for disproof). Nothing here re-implements that check.

Pure stdlib. Deterministic. No governance, no domain, no model."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Mapping, Optional, Sequence

from .subsumption import holds, neg
from .cross_subsumption import Verdict


class Standard(IntEnum):
    """Standard-of-proof scale (O104), ascending in stringency.

    An :class:`~enum.IntEnum` so that "does this clear the bar?" is the enum's
    own ``>=`` comparison — no hand-rolled rank table to drift out of sync."""

    GLAUBHAFT = 1                 # Glaubhaftmachung — mere plausibility
    PREPONDERANCE = 2             # balance of probabilities (> 50 %)
    CLEAR_AND_CONVINCING = 3      # a heightened civil standard
    BEYOND_REASONABLE_DOUBT = 4  # the criminal standard


# Ascending, for iteration / serialisation.
STANDARDS: tuple[Standard, ...] = (
    Standard.GLAUBHAFT,
    Standard.PREPONDERANCE,
    Standard.CLEAR_AND_CONVINCING,
    Standard.BEYOND_REASONABLE_DOUBT,
)

# Element status is the package's one shared three-valued verdict — the burden
# domain does not mint a parallel vocabulary. The proof reading maps onto it:
# proven → Verdict.SATISFIED, disproven → Verdict.NOT_SATISFIED, and *non-liquet*
# (the element left un-established) → Verdict.OPEN. The distinctively-legal reading
# (that OPEN here was decided *by the burden rule*, not by evidence) survives in the
# ElementFinding.by_burden / against / presumed fields, not in a second status enum.


def meets(attained: Standard, required: Standard) -> bool:
    """Does the ``attained`` degree of proof clear the ``required`` threshold?"""
    return attained >= required


@dataclass(frozen=True)
class Element:
    """One element of the claim and who must prove it.

    ``production`` defaults to ``''`` meaning *same party as persuasion* — the
    common case where whoever must ultimately convince also must come forward."""

    id: str                                       # the literal naming this element's fact
    persuasion: str                               # party bearing the burden of persuasion (O103)
    production: str = ""                          # party bearing the burden of production (O102)
    standard: Standard = Standard.PREPONDERANCE   # threshold this element must clear (O104)


@dataclass(frozen=True)
class Presumption:
    """A rebuttable presumption that supplies a fact until rebutted (O105).

    Once every literal in ``basic_facts`` holds, the presumption *triggers* and
    establishes ``supplies`` — unless any literal in ``rebutted_by`` also holds,
    in which case it is defeated and drops out of the analysis."""

    supplies: str                # element literal it establishes
    basic_facts: tuple = ()      # predicate facts that must hold to trigger it
    rebutted_by: tuple = ()      # literals that, if they hold, defeat the presumption


@dataclass(frozen=True)
class ElementFinding:
    """The disposition of a single element after allocation."""

    element: str
    status: Verdict                      # SATISFIED | NOT_SATISFIED | OPEN (proven | disproven | non-liquet)
    established: bool                     # operative finding: is the element taken as true?
    by_burden: bool                      # True iff decided by the burden rule (non-liquet), not by fact (O107)
    against: str                         # party the non-liquet ran against ('' otherwise)
    presumed: bool                       # True iff a presumption supplied it (O105)
    standard_required: Standard
    standard_attained: Optional[Standard]

    def to_dict(self) -> dict:
        """Plain-``dict`` projection with the enums lowered to their names."""
        return {
            "element": self.element,
            "status": self.status,
            "established": self.established,
            "by_burden": self.by_burden,
            "against": self.against,
            "presumed": self.presumed,
            "standard_required": self.standard_required.name,
            "standard_attained": (
                self.standard_attained.name
                if self.standard_attained is not None
                else None
            ),
        }


@dataclass(frozen=True)
class BurdenReport:
    """The allocation of every element of a claim, in input order."""

    findings: tuple = ()         # tuple[ElementFinding]

    def finding_for(self, element: str) -> Optional[ElementFinding]:
        """The finding for ``element``, or ``None`` if it was not allocated."""
        for f in self.findings:
            if f.element == element:
                return f
        return None

    def all_established(self) -> bool:
        """Every element established ⇒ the claim is made out."""
        return all(f.established for f in self.findings)

    def to_dict(self) -> dict:
        return {"findings": [f.to_dict() for f in self.findings]}


def _presumption_for(
    element: Element,
    facts: set,
    presumptions: Sequence[Presumption],
) -> bool:
    """Is there a triggered, unrebutted presumption supplying ``element.id``?

    Triggered ⇔ every ``basic_facts`` literal holds; unrebutted ⇔ no
    ``rebutted_by`` literal holds. Both use the consumed closed-world
    :func:`~loomground_solver.subsumption.holds`."""
    for p in presumptions:
        if p.supplies != element.id:
            continue
        triggered = all(holds(bf, facts) for bf in p.basic_facts)
        rebutted = any(holds(rb, facts) for rb in p.rebutted_by)
        if triggered and not rebutted:
            return True
    return False


def allocate(
    elements: Sequence[Element],
    facts: set,
    *,
    proof: Optional[Mapping[str, Standard]] = None,
    presumptions: Sequence[Presumption] = (),
) -> BurdenReport:
    """Allocate the burden across every element of a claim (O102-O107).

    For each element, in input order:

    1. A triggered, unrebutted :class:`Presumption` ⇒ ``Verdict.SATISFIED``
       (*proven*) / ``presumed``.
    2. Else if the element is *disproven on the merits* — ``holds(neg(id))`` and
       not ``holds(id)`` — ⇒ ``Verdict.NOT_SATISFIED`` (*disproven*; ``by_burden``
       False: decided by fact).
    3. Else ``Verdict.SATISFIED`` (*proven*) iff :func:`meets` — where the attained
       degree is ``proof[id]`` if supplied, otherwise the required standard when
       ``holds(id)`` and ``None`` when the element is simply absent.
    4. Else ``Verdict.OPEN`` (*non-liquet*): the element is left **un-established** and decided
       **by the burden rule against** ``Element.persuasion`` (O107). The fact is
       never guessed.
    """
    proof = proof or {}
    findings: list[ElementFinding] = []

    for e in elements:
        required = e.standard

        # (1) Presumption supplies the fact.
        if _presumption_for(e, facts, presumptions):
            findings.append(
                ElementFinding(
                    element=e.id,
                    status=Verdict.SATISFIED,
                    established=True,
                    by_burden=False,
                    against="",
                    presumed=True,
                    standard_required=required,
                    standard_attained=required,
                )
            )
            continue

        # (2) Disproven on the merits.
        if holds(neg(e.id), facts) and not holds(e.id, facts):
            findings.append(
                ElementFinding(
                    element=e.id,
                    status=Verdict.NOT_SATISFIED,
                    established=False,
                    by_burden=False,
                    against="",
                    presumed=False,
                    standard_required=required,
                    standard_attained=None,
                )
            )
            continue

        # (3) Proven iff the attained degree of proof clears the threshold.
        if e.id in proof:
            attained: Optional[Standard] = proof[e.id]
        elif holds(e.id, facts):
            attained = required
        else:
            attained = None

        if attained is not None and meets(attained, required):
            findings.append(
                ElementFinding(
                    element=e.id,
                    status=Verdict.SATISFIED,
                    established=True,
                    by_burden=False,
                    against="",
                    presumed=False,
                    standard_required=required,
                    standard_attained=attained,
                )
            )
            continue

        # (4) Non-liquet: un-established, decided by the burden of persuasion.
        findings.append(
            ElementFinding(
                element=e.id,
                status=Verdict.OPEN,
                established=False,
                by_burden=True,
                against=e.persuasion,
                presumed=False,
                standard_required=required,
                standard_attained=attained,
            )
        )

    return BurdenReport(findings=tuple(findings))
