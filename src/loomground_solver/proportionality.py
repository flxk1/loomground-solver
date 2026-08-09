# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Structured proportionality (Verhältnismäßigkeit) + Alexy's Weight Formula
(O94–O99, Family K) — COMPUTES from supplied inputs; it never fabricates a winner.

A principle-collision (routed here from :mod:`loomground_solver.principles`) is
weighed through the four canonical prongs, evaluated in order:

* **O94 legitimate aim** (legitimer Zweck) — an admissibility flag on the pursued
  aim (supplied);
* **O95 suitability** (Geeignetheit) — the means can further the aim (supplied
  boolean);
* **O96 necessity** (Erforderlichkeit) — no supplied alternative is *equally
  effective AND less intrusive* than the chosen means (a dominance check over the
  given alternatives — nothing is assumed about means not supplied);
* **O97/O98 proportionality stricto sensu** (Angemessenheit) — Alexy's Weight
  Formula ``W = (I_i·G_i·R_i) / (I_j·G_j·R_j)`` over the two colliding principles,
  each variable on the triadic scale light/moderate/serious = ``2^0/2^1/2^2``.

**O99 outcome.** ``W > 1`` ⇒ side *i* prevails; ``W < 1`` ⇒ side *j* prevails. A
genuine balancing tie (``W == 1``) **or** any prong that fails or is undecidable
means the balance did not settle — the engine returns
:data:`loomground_solver.relation.ESCALATE` (the one escalate-don't-guess
sentinel), never a coin-flipped winner. The failing prong is recorded so the
escalation is never silent.

Honesty floor (by construction): the interest-weights are **inputs**. Every
triadic label is required and validated; an unknown or omitted weight is a
construction error, never a silent default. The comparison ``W == 1`` is exact —
products of powers of two — so a tie is a real tie, not float noise.

Pure stdlib, deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Union

from .relation import ESCALATE, _Escalate

# ── triadic intensity scale: light/moderate/serious = 2^0 / 2^1 / 2^2 ─────────
LIGHT = "light"
MODERATE = "moderate"
SERIOUS = "serious"

TRIAD: dict[str, int] = {LIGHT: 1, MODERATE: 2, SERIOUS: 4}  # 2**0, 2**1, 2**2

# ── prong identifiers ─────────────────────────────────────────────────────────
LEGITIMATE_AIM = "legitimate-aim"   # O94
SUITABILITY = "suitability"         # O95
NECESSITY = "necessity"             # O96
STRICTO_SENSU = "stricto-sensu"     # O97/O98

# ── outcome labels ────────────────────────────────────────────────────────────
I_PREVAILS = "i-prevails"
J_PREVAILS = "j-prevails"
ESCALATE_OUTCOME = "escalate"


def _weight(name: str, label: str) -> int:
    """Map a triadic label to its factor, fail-closed. A weight is an input; an
    unknown label is never coerced to a default (honesty floor)."""
    try:
        return TRIAD[label]
    except KeyError:
        raise ValueError(
            f"{name} must be one of {sorted(TRIAD)}, got {label!r} "
            "(interest-weights are inputs; they are never defaulted)"
        ) from None


@dataclass(frozen=True)
class PrincipleWeight:
    """One side of the collision on Alexy's three variables, each triadic.

    ``intensity`` is I (interference intensity for the burdened side / satisfaction
    importance for the promoted side), ``abstract_weight`` is G (the abstract
    weight of the principle), ``reliability`` is R (the epistemic reliability of
    the empirical premises). All three are supplied triadic labels."""

    label: str
    intensity: str
    abstract_weight: str
    reliability: str

    def factors(self) -> tuple:
        return (
            _weight("intensity", self.intensity),
            _weight("abstract_weight", self.abstract_weight),
            _weight("reliability", self.reliability),
        )

    def product(self) -> int:
        """``I · G · R`` — the numerator (side i) or denominator (side j)."""
        i, g, r = self.factors()
        return i * g * r


@dataclass(frozen=True)
class Alternative:
    """A candidate milder means for the necessity check. ``effectiveness`` and
    ``intrusiveness`` are triadic labels (light/moderate/serious)."""

    label: str
    effectiveness: str
    intrusiveness: str


@dataclass(frozen=True)
class ProngVerdict:
    prong: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {"prong": self.prong, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class ProportionalityResult:
    """The four prong verdicts, the Weight-Formula value, and the O99 outcome.

    ``prevailing`` is the *label* of the winning side, or the
    :data:`loomground_solver.relation.ESCALATE` sentinel on a tie / failed prong —
    never a fabricated winner. ``weight`` is ``None`` when balancing was not
    reached (an earlier prong failed)."""

    aim: str
    prongs: tuple                       # tuple[ProngVerdict]
    weight: Optional[float]
    prevailing: Union[str, _Escalate]   # side label, or ESCALATE
    outcome: str
    reason: str

    def escalated(self) -> bool:
        return self.prevailing is ESCALATE

    def prong(self, name: str) -> Optional[ProngVerdict]:
        for p in self.prongs:
            if p.prong == name:
                return p
        return None

    def to_dict(self) -> dict:
        return {
            "aim": self.aim,
            "prongs": [p.to_dict() for p in self.prongs],
            "weight": self.weight,
            # ESCALATE never renders as a winner label
            "prevailing": "ESCALATE" if self.escalated() else self.prevailing,
            "outcome": self.outcome,
            "reason": self.reason,
        }


def necessity_holds(
    means_effectiveness: str,
    means_intrusiveness: str,
    alternatives: Sequence[Alternative],
) -> tuple:
    """O96 dominance check. Necessity HOLDS iff no supplied alternative is *at
    least as effective* as the means AND *strictly less intrusive*. Returns
    ``(passed, dominating_label_or_None)``; nothing is assumed about means the
    caller did not supply."""
    e_means = _weight("means_effectiveness", means_effectiveness)
    x_means = _weight("means_intrusiveness", means_intrusiveness)
    for alt in alternatives:
        e_alt = _weight(f"alternative[{alt.label}].effectiveness", alt.effectiveness)
        x_alt = _weight(f"alternative[{alt.label}].intrusiveness", alt.intrusiveness)
        if e_alt >= e_means and x_alt < x_means:
            return False, alt.label
    return True, None


def weight_formula(side_i: PrincipleWeight, side_j: PrincipleWeight) -> float:
    """Alexy's Weight Formula ``W = (I_i·G_i·R_i) / (I_j·G_j·R_j)`` as a float.
    The tie test in :func:`proportionality` uses the exact integer products, not
    this float."""
    return side_i.product() / side_j.product()


def proportionality(
    *,
    aim: str,
    legitimate: bool,
    suitable: bool,
    means_effectiveness: str,
    means_intrusiveness: str,
    alternatives: Sequence[Alternative],
    side_i: PrincipleWeight,
    side_j: PrincipleWeight,
) -> ProportionalityResult:
    """Run the four-prong test and return the structured result (O94–O99).

    Prongs are evaluated in order; the first that fails short-circuits to
    :data:`loomground_solver.relation.ESCALATE` (balancing did not settle — do not
    fabricate a winner). Reaching stricto sensu, ``W > 1`` ⇒ ``side_i`` prevails,
    ``W < 1`` ⇒ ``side_j``, and an exact ``W == 1`` ⇒ tie ⇒ ESCALATE.

    All triadic weights are required inputs; an unknown label raises
    :class:`ValueError` rather than defaulting (honesty floor).
    """
    prongs: list = []

    # O94 — legitimate aim
    ok_aim = bool(legitimate)
    prongs.append(ProngVerdict(LEGITIMATE_AIM, ok_aim,
                               "aim admissible" if ok_aim else "aim not established"))
    if not ok_aim:
        return ProportionalityResult(
            aim, tuple(prongs), None, ESCALATE, ESCALATE_OUTCOME,
            "legitimate-aim prong failed — no legitimate aim to balance for")

    # O95 — suitability (Geeignetheit)
    ok_suit = bool(suitable)
    prongs.append(ProngVerdict(SUITABILITY, ok_suit,
                               "means furthers the aim" if ok_suit
                               else "means does not further the aim"))
    if not ok_suit:
        return ProportionalityResult(
            aim, tuple(prongs), None, ESCALATE, ESCALATE_OUTCOME,
            "suitability prong failed — means cannot further the aim")

    # O96 — necessity (Erforderlichkeit)
    ok_nec, dominating = necessity_holds(
        means_effectiveness, means_intrusiveness, alternatives)
    prongs.append(ProngVerdict(
        NECESSITY, ok_nec,
        "no milder equally-effective means supplied" if ok_nec
        else f"alternative {dominating!r} is equally effective and less intrusive"))
    if not ok_nec:
        return ProportionalityResult(
            aim, tuple(prongs), None, ESCALATE, ESCALATE_OUTCOME,
            f"necessity prong failed — milder means {dominating!r} available")

    # O97/O98 — proportionality stricto sensu (Angemessenheit): Weight Formula
    num, den = side_i.product(), side_j.product()
    w = num / den
    if num > den:
        prongs.append(ProngVerdict(STRICTO_SENSU, True,
                                   f"W={w} > 1 — {side_i.label} outweighs {side_j.label}"))
        return ProportionalityResult(aim, tuple(prongs), w, side_i.label,
                                     I_PREVAILS, f"{side_i.label} prevails (W={w})")
    if num < den:
        prongs.append(ProngVerdict(STRICTO_SENSU, True,
                                   f"W={w} < 1 — {side_j.label} outweighs {side_i.label}"))
        return ProportionalityResult(aim, tuple(prongs), w, side_j.label,
                                     J_PREVAILS, f"{side_j.label} prevails (W={w})")
    # num == den — an exact balancing tie: escalate, never coin-flip a winner
    prongs.append(ProngVerdict(STRICTO_SENSU, False,
                               f"W={w} == 1 — the principles are in exact balance"))
    return ProportionalityResult(
        aim, tuple(prongs), w, ESCALATE, ESCALATE_OUTCOME,
        "stricto-sensu tie (W==1) — balance undecided, human resolution required")
