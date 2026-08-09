# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Formal justice screen (O154, FORMAL-SCREEN HALF) — FLAG ONLY, never a verdict.

The anti-blindness gate has two halves. The *substantive* half (equity O145,
Radbruch O137) needs grounded values and is deliberately out of scope here. This
module is the buildable, value-grounding-free half: it runs the formal checks the
package already ships and, when any of them trips, **recommends** demoting a
decided case's terminal state from ``DETERMINATE`` to ``ESCALATE``.

It composes — it does not re-implement — two existing instruments:

* :func:`loomground_solver.consistency.check_consistency` (O151) — treat-like-alike
  over the surrounding case set, plus the direct-discrimination specialisation
  :func:`~loomground_solver.consistency.check_nondiscrimination`;
* :func:`loomground_solver.distribution.adverse_impact` (O152) — the four-fifths
  disparity flag, fed by :func:`~loomground_solver.distribution.rates_from_cases`.

The ``ESCALATE`` recommendation label is *sourced* from
:data:`loomground_solver.relation.ESCALATE` (the package's one escalation token),
never a fresh literal.

BOUNDARY (by construction): this op RECOMMENDS/FLAGS only. It returns a demote
flag and the tripped reasons; it never labels a decision "unjust", never emits a
verdict, and never itself changes the disposition — the caller decides what to do
with the recommendation. An op that adjudicates would be wrong here. Pure stdlib,
deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Optional, Sequence, Union

from .consistency import (
    ConsistencyReport,
    DecidedCase,
    check_consistency,
    check_nondiscrimination,
)
from .distribution import FOUR_FIFTHS, ImpactRatio, adverse_impact, rates_from_cases
from .relation import ESCALATE as _ESCALATE

# ── terminal-state labels ─────────────────────────────────────────────────────
# The disposition a decided case carries in, and the label recommended in its
# place when a formal check trips. ``ESCALATE`` is sourced from the package's one
# escalation token (``relation.ESCALATE``) rather than duplicated as a literal.
DETERMINATE: str = "DETERMINATE"
ESCALATE: str = str(_ESCALATE)  # "ESCALATE"

# ── reason codes (which formal check tripped) ─────────────────────────────────
INCONSISTENCY = "inconsistency"        # O151 treat-like-alike breach
DISCRIMINATION = "discrimination"      # O151 direct-discrimination specialisation
ADVERSE_IMPACT = "adverse-impact"      # O152 four-fifths disparity flag


@dataclass(frozen=True)
class TrippedReason:
    """One formal check that tripped, with its supporting detail.

    ``check`` is one of :data:`INCONSISTENCY` / :data:`DISCRIMINATION` /
    :data:`ADVERSE_IMPACT`. ``detail`` is the offending sub-report's own
    ``to_dict`` projection — evidence for the recommendation, not a verdict.
    """

    check: str
    detail: dict

    def to_dict(self) -> dict:
        return {"check": self.check, "detail": self.detail}


@dataclass(frozen=True)
class ScreenResult:
    """The recommendation of the formal screen — a flag, never a verdict.

    ``demote`` True means: *recommend* moving ``disposition`` (``DETERMINATE``) to
    ``recommended`` (``ESCALATE``). The screen does not itself change anything and
    never labels the decision "unjust"; it only reports which formal checks
    tripped.
    """

    case_id: str
    disposition: str                     # the incoming terminal state
    recommended: str                     # ESCALATE when demote, else disposition unchanged
    demote: bool                         # True iff any formal check tripped (a RECOMMENDATION)
    reasons: tuple                       # tuple[TrippedReason], order-stable by check code
    consistency: ConsistencyReport       # the full O151 report (transparency)
    nondiscrimination: Optional[ConsistencyReport]  # O151 protected-attr report, if requested
    impact: Optional[ImpactRatio]        # the full O152 report, if requested

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "disposition": self.disposition,
            "recommended": self.recommended,
            "demote": self.demote,
            "reasons": [r.to_dict() for r in self.reasons],
            "consistency": self.consistency.to_dict(),
            "nondiscrimination": (
                self.nondiscrimination.to_dict()
                if self.nondiscrimination is not None
                else None
            ),
            "impact": self.impact.to_dict() if self.impact is not None else None,
        }


def _focal_pairs(report: ConsistencyReport, case_id: str, focal_only: bool) -> tuple:
    """The report's pairs, optionally narrowed to those touching ``case_id``."""
    if not focal_only:
        return report.pairs
    return tuple(p for p in report.pairs if case_id in (p.left, p.right))


def justice_screen(
    case_id: str,
    cases: Sequence[DecidedCase],
    *,
    relevant_keys: Iterable[str],
    disposition: str = DETERMINATE,
    protected_keys: Optional[Iterable[str]] = None,
    group_key: Optional[str] = None,
    favourable: Union[set, Callable[[str], bool], None] = None,
    threshold: float = FOUR_FIFTHS,
    focal_only: bool = False,
) -> ScreenResult:
    """Run the formal justice checks over ``cases`` and recommend escalation.

    ``case_id`` names the focal decided case whose ``disposition`` is under
    screening; ``cases`` is the surrounding case set it belongs to. Each check is
    run by composing an existing instrument:

    * **O151 treat-like-alike** — :func:`consistency.check_consistency` over
      ``relevant_keys``; a breach trips :data:`INCONSISTENCY`.
    * **O151 direct discrimination** (only when ``protected_keys`` is given) —
      :func:`consistency.check_nondiscrimination`; a breach trips
      :data:`DISCRIMINATION`.
    * **O152 adverse impact** (only when both ``group_key`` and ``favourable`` are
      given) — :func:`distribution.rates_from_cases` into
      :func:`distribution.adverse_impact` at ``threshold``; a ``breaches`` trips
      :data:`ADVERSE_IMPACT`.

    With ``focal_only`` True the pairwise checks trip only when an offending pair
    involves ``case_id`` (the aggregate adverse-impact flag is unaffected).

    Returns a :class:`ScreenResult`. ``demote`` is True iff any check tripped, in
    which case ``recommended`` is :data:`ESCALATE`; otherwise ``recommended`` is
    ``disposition`` unchanged. This is a RECOMMENDATION only — the op never labels
    the decision "unjust" and never itself decides.
    """
    reasons: list[TrippedReason] = []

    # O151 — treat-like-alike over the relevant features.
    consistency = check_consistency(cases, relevant_keys)
    cons_pairs = _focal_pairs(consistency, case_id, focal_only)
    if cons_pairs:
        reasons.append(TrippedReason(
            INCONSISTENCY, {"pairs": [p.to_dict() for p in cons_pairs]}))

    # O151 — direct-discrimination specialisation (opt-in).
    nondiscrimination: Optional[ConsistencyReport] = None
    if protected_keys is not None:
        nondiscrimination = check_nondiscrimination(cases, protected_keys)
        nd_pairs = _focal_pairs(nondiscrimination, case_id, focal_only)
        if nd_pairs:
            reasons.append(TrippedReason(
                DISCRIMINATION, {"pairs": [p.to_dict() for p in nd_pairs]}))

    # O152 — four-fifths adverse-impact disparity (opt-in; aggregate).
    impact: Optional[ImpactRatio] = None
    if group_key is not None and favourable is not None:
        counts = rates_from_cases(cases, group_key=group_key, favourable=favourable)
        impact = adverse_impact(counts, threshold=threshold)
        if impact.breaches:
            reasons.append(TrippedReason(
                ADVERSE_IMPACT, {"impact": impact.to_dict()}))

    # Stable order by reason code so serialisation is deterministic.
    reasons.sort(key=lambda r: r.check)

    demote = bool(reasons)
    recommended = ESCALATE if demote else disposition
    return ScreenResult(
        case_id=case_id,
        disposition=disposition,
        recommended=recommended,
        demote=demote,
        reasons=tuple(reasons),
        consistency=consistency,
        nondiscrimination=nondiscrimination,
        impact=impact,
    )
