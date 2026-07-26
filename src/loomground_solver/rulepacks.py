# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Typed inference rule-packs — the pluggable half of the universal solver.

The kernel is mode-free: it reasons over the universal form. WHAT counts as a
valid inference, and how competing normative conclusions are resolved, is data —
a *rule-pack*, plugged in exactly like a render profile. This module ships two:

  * ``GENERIC_PACK`` — no ordering: any genuine contradiction ESCALATES (the safe
    default; nothing auto-resolves).
  * ``LEX_CONFLICT_PACK`` — the classical defeaters, in priority order:
    lex superior (rank) ▷ lex specialis (specificity) ▷ lex posterior (time).
    Domain-general jurisprudence, not a jurisdiction: the concrete rank/
    specificity/time values are supplied by the caller (or a legal profile).

A pack never fabricates a winner it cannot justify: if two contradictory norms
are equal on every ordering the pack knows, the collision is GENUINE and must
escalate — the norm_contract NT-6 discipline, made operational.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Contradiction: a pair of deontic modals that cannot both hold of one act.
CONTRADICTIONS = (
    frozenset({"obligatory", "prohibited"}),
    frozenset({"permitted", "prohibited"}),
)


def contradicts(a: str, b: str) -> bool:
    """True iff two deontic modals clash on the same act."""
    return frozenset({a, b}) in CONTRADICTIONS


@dataclass(frozen=True)
class Ordering:
    """One defeater: the attribute it ranks on and a human name. Higher wins."""
    name: str          # 'lex-superior' | 'lex-specialis' | 'lex-posterior' | …
    attr: str          # the Norm attribute compared: 'rank' | 'specificity' | 'time'


@dataclass(frozen=True)
class RulePack:
    """A named, pluggable set of conflict orderings + a modal frame label.

    ``orderings`` is applied in list order (first ordering that separates the two
    norms decides the winner). Empty ⇒ nothing auto-resolves ⇒ every contradiction
    is a genuine collision (escalate)."""
    name: str
    orderings: tuple = ()
    frame: str = "deontic"      # 'deontic' | 'epistemic' — how the pack reasons

    def resolve(self, a, b) -> Optional[str]:
        """Given two contradictory norms, return the WINNER ('a' | 'b') by the
        first ordering that separates them, or None if they are equal on all —
        a genuine, non-auto-resolvable collision."""
        for o in self.orderings:
            va, vb = getattr(a, o.attr, 0), getattr(b, o.attr, 0)
            if va != vb:
                return "a" if va > vb else "b"
        return None

    def separating_rule(self, a, b) -> Optional[str]:
        """Name of the ordering that decided the winner (provenance), or None."""
        for o in self.orderings:
            if getattr(a, o.attr, 0) != getattr(b, o.attr, 0):
                return o.name
        return None


GENERIC_PACK = RulePack("generic", orderings=(), frame="deontic")

LEX_CONFLICT_PACK = RulePack(
    "lex-conflict",
    orderings=(
        Ordering("lex-superior", "rank"),
        Ordering("lex-specialis", "specificity"),
        Ordering("lex-posterior", "time"),
    ),
    frame="deontic",
)

PACKS = {p.name: p for p in (GENERIC_PACK, LEX_CONFLICT_PACK)}
