# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Deontic permissive/prohibitive closure with polarity (O140).

A *closure* answers, for a single act, the residual question the scenario
resolver leaves open: when no express deontic norm decides the act, what is its
status *by default*? That default is not a constant — it is a property of the
agent's normative posture:

  * **PRIVATE** posture (residual liberty / the closure of the permitted):
    *what is not forbidden is permitted* — a citizen may do anything not banned.
    The default answer is a **weak** permission.
  * **PUBLIC** posture (competence principle / the closure of the prohibited):
    *what is not permitted is forbidden* — an organ of the state may do only what
    it is empowered to do. The default answer is a prohibition.

This module CONSUMES the scenario conflict-resolution (:func:`scenario.derive`,
the ONE shared grounded resolver) — it never re-derives who wins a collision —
and the deontic O/P/F vocabulary (:mod:`deontic.operators`). It adds exactly one
thing on top: the polarity of the residual default and the strong/weak marking of
a permission. A genuine, unresolved collision does NOT get a forced closure: it
ESCALATES (``open=True``), preserving the norm_contract NT-6 discipline the
resolver already enforces. Pure: no governance, no domain, no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from .rulepacks import RulePack, GENERIC_PACK
from .scenario import Norm, Scenario, derive, ActResolution
from deontic.operators import (
    OP_OBLIGATION, OP_PERMISSION, OP_PROHIBITION, VALID_OPERATORS, gloss,
)


class AgentMode(str, Enum):
    """The normative posture that fixes the residual default."""
    PRIVATE = "private"   # residual liberty: what is not forbidden is (weakly) permitted
    PUBLIC = "public"     # competence principle: what is not permitted is forbidden


# The scenario layer speaks 'obligatory'|'permitted'|'prohibited'; the deontic
# language glosses OP_PROHIBITION ('F') as 'forbidden'. These synonyms bridge the
# ONE vocabulary gap ('prohibited' vs 'forbidden') so the mapping below can be
# built purely from the published deontic constants + gloss — no hand-rolled table.
_VERDICT_SYNONYMS = {"prohibited": gloss(OP_PROHIBITION)}


def verdict_to_operator(verdict: Optional[str]) -> str:
    """Map a scenario verdict onto its deontic operator.

    Returns one of :data:`deontic.operators.VALID_OPERATORS`, or ``''`` when the
    verdict is empty/None or has no deontic operator. The lookup is derived from
    ``gloss`` over ``VALID_OPERATORS`` (bridging the 'prohibited'/'forbidden'
    wording gap), never from a duplicated literal table.
    """
    if not verdict:
        return ""
    by_gloss = {gloss(op): op for op in VALID_OPERATORS}
    key = _VERDICT_SYNONYMS.get(verdict, verdict)
    return by_gloss.get(key, "")


STRONG = "strong"   # an express deontic norm (P/O/F) fired for the act
WEAK = "weak"       # residual liberty from the PRIVATE-mode default


@dataclass(frozen=True)
class ClosureResult:
    """The closed deontic status of one act under a given posture."""
    act: str
    verdict: Optional[str]              # 'obligatory'|'permitted'|'prohibited'|None (open)
    operator: str                      # deontic O/P/F ('' when open)
    gloss: str                         # deontic gloss of the operator
    fired: bool                        # True iff an express norm decided the act
    residual: bool                     # True iff the mode default supplied the answer
    permission_strength: Optional[str]  # 'strong' | 'weak' | None (not a permission)
    open: bool                         # True iff an unresolved collision escalated -> no closure
    survivors: tuple                   # sources of the firing/surviving norms
    mode: AgentMode

    def to_dict(self) -> dict:
        return {
            "act": self.act,
            "verdict": self.verdict,
            "operator": self.operator,
            "gloss": self.gloss,
            "fired": self.fired,
            "residual": self.residual,
            "permission_strength": self.permission_strength,
            "open": self.open,
            "survivors": list(self.survivors),
            "mode": self.mode.value,
        }


def _residual(act: str, mode: AgentMode, survivors: tuple) -> ClosureResult:
    """The mode default when no express norm fires (and no collision escalates)."""
    if mode is AgentMode.PRIVATE:
        # residual liberty: not forbidden => weakly permitted
        op = OP_PERMISSION
        return ClosureResult(
            act=act, verdict="permitted", operator=op, gloss=gloss(op),
            fired=False, residual=True, permission_strength=WEAK, open=False,
            survivors=survivors, mode=mode,
        )
    # competence principle: not permitted => forbidden
    op = OP_PROHIBITION
    return ClosureResult(
        act=act, verdict="prohibited", operator=op, gloss=gloss(op),
        fired=False, residual=True, permission_strength=None, open=False,
        survivors=survivors, mode=mode,
    )


def close(act: str, norms: Sequence[Norm], *, mode: AgentMode,
          pack: RulePack = GENERIC_PACK) -> ClosureResult:
    """Close the deontic status of ``act`` under ``mode``.

    The norms touching ``act`` are resolved by :func:`scenario.derive` — the one
    shared grounded resolver — under ``pack``; closure is then applied:

      * an unresolved collision (:attr:`ActResolution.collisions`) ⇒ ``open=True``,
        no closure forced (escalate);
      * a determinate verdict ⇒ ``fired=True``; a surviving 'permitted' verdict is
        a **STRONG** permission;
      * nothing fires (no resolution for the act, or a verdict of None with no
        collision) ⇒ the mode's residual default: PRIVATE ⇒ weakly permitted,
        PUBLIC ⇒ prohibited.
    """
    scenario = Scenario(id="closure", norms=list(norms))
    result = derive(scenario, pack=pack)
    r: Optional[ActResolution] = result.resolution_for(act)

    # An unresolved collision escalates — closure is NOT forced.
    if r is not None and r.collisions:
        return ClosureResult(
            act=act, verdict=None, operator="", gloss=gloss(""),
            fired=False, residual=False, permission_strength=None, open=True,
            survivors=tuple(r.survivors), mode=mode,
        )

    # No express norm decided the act -> residual default by posture.
    if r is None or r.verdict is None:
        survivors = tuple(r.survivors) if r is not None else ()
        return _residual(act, mode, survivors)

    # A determinate verdict fired.
    op = verdict_to_operator(r.verdict)
    strength = STRONG if r.verdict == "permitted" else None
    return ClosureResult(
        act=act, verdict=r.verdict, operator=op, gloss=gloss(op),
        fired=True, residual=False, permission_strength=strength, open=False,
        survivors=tuple(r.survivors), mode=mode,
    )


def is_strong_permission(r: ClosureResult) -> bool:
    """True iff ``r`` is an express (strong) permission rather than residual liberty."""
    return r.verdict == "permitted" and r.permission_strength == STRONG
