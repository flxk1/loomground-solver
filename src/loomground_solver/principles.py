# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Collision-of-principles detection + rule/principle routing (O93) — DETECT AND
ROUTE ONLY; it never resolves the collision.

Two norms can clash on one act. *How* that clash may be answered depends on the
character of the colliding norms (Dworkin's distinction, Alexy's collision law):

* a **RULE** applies in an all-or-nothing fashion. Two contradictory rules on one
  act are a **rule-collision**: exactly one must give way, and the classical
  defeaters settle which (lex superior / specialis / posterior — Family I,
  :data:`loomground_solver.rulepacks.LEX_CONFLICT_PACK`). The routing target is
  *lex-ordering*.
* a **PRINCIPLE** is an optimisation requirement satisfiable to degrees. A clash
  in which at least one side is a principle admits **no** all-or-nothing answer —
  neither side is simply invalidated; they are weighed under the circumstances.
  The routing target is *balancing* (proportionality, Family K —
  :mod:`loomground_solver.proportionality`).

This module answers only *which kind of collision this is, and where it must be
sent*. It does **not** run the lex-ordering and it does **not** run the balancing;
those are the resolvers it routes to. Detection of the underlying clash is not
re-implemented here either: it consumes
:func:`loomground_solver.rulepacks.contradicts`, the one deontic-clash predicate
the package already ships.

Pure stdlib, deterministic. Characters are **inputs**: an unknown character is a
construction error (fail-closed), never silently coerced — the module invents no
character it was not given.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .rulepacks import contradicts
from .scenario import Norm

# ── norm character ────────────────────────────────────────────────────────────
RULE = "rule"            # all-or-nothing: valid ⇒ applies; a clash invalidates one
PRINCIPLE = "principle"  # optimisation requirement: satisfiable to a degree

_CHARACTERS = frozenset({RULE, PRINCIPLE})

# ── collision kinds ───────────────────────────────────────────────────────────
NO_COLLISION = "no-collision"              # the modals do not clash on this act
RULE_COLLISION = "rule-collision"          # both sides are rules
PRINCIPLE_COLLISION = "principle-collision"  # at least one side is a principle

# ── routing targets (this module ROUTES; the target RESOLVES) ─────────────────
ROUTE_NONE = "none"                # nothing to resolve
ROUTE_LEX_ORDERING = "lex-ordering"  # Family I: rulepacks.LEX_CONFLICT_PACK
ROUTE_BALANCING = "balancing"      # Family K: proportionality.proportionality


def _check_character(name: str, value: str) -> None:
    if value not in _CHARACTERS:
        raise ValueError(
            f"{name} must be one of {sorted(_CHARACTERS)}, got {value!r} "
            "(character is an input; it is never inferred)"
        )


@dataclass(frozen=True)
class CollisionRouting:
    """The classification of a two-norm clash and where it must be sent.

    ``kind`` is one of :data:`NO_COLLISION` / :data:`RULE_COLLISION` /
    :data:`PRINCIPLE_COLLISION`; ``route`` names the resolver the clash is handed
    to and is deliberately *not* a verdict — no winner is recorded here."""

    act: str
    collides: bool
    kind: str
    route: str
    characters: tuple          # (character_a, character_b)
    modals: tuple              # (deontic_a, deontic_b)

    def to_dict(self) -> dict:
        return {
            "act": self.act,
            "collides": self.collides,
            "kind": self.kind,
            "route": self.route,
            "characters": list(self.characters),
            "modals": list(self.modals),
        }


def classify_collision(
    a: Norm,
    b: Norm,
    *,
    character_a: str,
    character_b: str,
) -> CollisionRouting:
    """Classify a clash between two norms on the **same** act and route it.

    ``character_a`` / ``character_b`` are each :data:`RULE` or :data:`PRINCIPLE`
    and are required — the character of a norm is supplied, never guessed.

    The underlying deontic clash is detected with
    :func:`loomground_solver.rulepacks.contradicts` (not re-implemented). When the
    two modals do not clash the result is :data:`NO_COLLISION` routed to
    :data:`ROUTE_NONE`. A clash of two rules is a :data:`RULE_COLLISION` routed to
    :data:`ROUTE_LEX_ORDERING`; a clash where either side is a principle is a
    :data:`PRINCIPLE_COLLISION` routed to :data:`ROUTE_BALANCING`.

    :raises ValueError: if the norms address different acts (a collision is
        defined on one act), or a character is not a known character.
    """
    if a.act != b.act:
        raise ValueError(
            f"a collision is defined on one act; got {a.act!r} vs {b.act!r}"
        )
    _check_character("character_a", character_a)
    _check_character("character_b", character_b)

    characters = (character_a, character_b)
    modals = (a.deontic, b.deontic)

    if not contradicts(a.deontic, b.deontic):
        return CollisionRouting(a.act, False, NO_COLLISION, ROUTE_NONE,
                                characters, modals)

    if character_a == RULE and character_b == RULE:
        return CollisionRouting(a.act, True, RULE_COLLISION, ROUTE_LEX_ORDERING,
                                characters, modals)

    return CollisionRouting(a.act, True, PRINCIPLE_COLLISION, ROUTE_BALANCING,
                            characters, modals)


def route_for(routing: CollisionRouting) -> Optional[str]:
    """The resolver a clash is sent to, or ``None`` when there is nothing to
    resolve. Convenience over :attr:`CollisionRouting.route`; still no verdict."""
    return None if routing.route == ROUTE_NONE else routing.route
