# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Quantitative condition evaluation — the numeric/quantity face of subsumption.

:mod:`cross_subsumption` routes a norm condition to one of the five reasoning
dimensions and lifts :func:`subsumption.holds` (a bool) into a three-valued
:class:`~cross_subsumption.Verdict` (SATISFIED / NOT_SATISFIED / **OPEN**). Its
TEMPORAL route does *date ordering* (before / after). But a norm antecedent
routinely rests on a **quantitative** predicate — "the amount exceeds
EUR 10,000", "the delay is at most 30 days", "the count is between 5 and 20" —
and nothing evaluated one. Feeding such a predicate to the flat closed-world
classifier would silently answer *unproven → not satisfied*, hiding that the
right evaluator was never run (the exact failure mode ``cross_subsumption``
exists to avoid).

This module is that evaluator. It **consumes** the substrate; it regrows none of
it:

  * :class:`predicate.Predicate` (``kind='threshold'``) + the shared comparator
    vocabulary :data:`predicate._COMPARATORS` — the parsed threshold struct
    (comparator + decimal value + optional unit) is the input, straight from
    :func:`predicate.parse_condition`;
  * :class:`temporal.Money` / :class:`temporal.Duration` /
    :class:`temporal.TemporalError` — the typed, Decimal-safe quantities a unit
    carries (a currency, a duration); no float ever enters a comparison;
  * :class:`cross_subsumption.Verdict` / :class:`cross_subsumption.DimVerdict` —
    the SHARED verdict + per-condition result type, so a
    :func:`evaluate_quantitative` result folds into
    :func:`cross_subsumption.subsume_antecedent`'s AND-with-OPEN-dominant
    aggregation exactly like a native ``_eval_*`` output;
  * :class:`dimensions.Dimension` — a duration comparison IS temporal reasoning,
    so it is tagged ``TEMPORAL``; money / scalar comparisons have no Dimension
    member and are honestly tagged ``None``.

It is **add-only**: it cannot touch ``subsume_across``'s fixed five-dimension
router nor add a ``QUANTITATIVE`` :class:`~dimensions.Dimension` member, so it
stands alongside as a standalone condition evaluator whose output type is
``DimVerdict``. A human can (a) call it directly, (b) fold its ``DimVerdict``
into :func:`~cross_subsumption.subsume_antecedent`, or (c) wire it into a future
QUANTITATIVE branch of ``subsume_across``.

Honesty is committed, not optional — mirroring ``_eval_temporal``'s
"operand ``None`` → OPEN, never guessed":

  1. **missing operand → OPEN** — no fact for the subject (absent key), or the
     fact is present-but-``None`` (unknown). Never a fabricated comparison.
  2. **unit mismatch → OPEN** — money-vs-duration, EUR-vs-USD, money-vs-scalar:
     the operands are incommensurable, so no comparison is invented.
  3. **calendar-ambiguous duration → OPEN** — a duration carrying months/years
     has no fixed magnitude without an anchor date; comparing it is OPEN, never
     guessed (mirrors ``Duration.add_to``'s refusal to invent an anchor).
  4. **decided otherwise** — a well-typed, commensurable comparison is
     SATISFIED or NOT_SATISFIED. Boundaries are exact: a closed bound includes
     its endpoint, an open bound excludes it.

Pure stdlib. No governance, no corpus, no domain: it imports neither
``loomground_legal`` nor ``loomground_versum``.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional

from .cross_subsumption import DimVerdict, Verdict
from .dimensions import Dimension
from .predicate import Predicate, _COMPARATORS
from .temporal import Duration, Money, TemporalError

__all__ = [
    "QuantError",
    "Interval",
    "QuantCondition",
    "evaluate_quantitative",
]


class QuantError(ValueError):
    """Raised when a quantitative condition is malformed at construction.

    Note the split from OPEN: a *malformed condition* (a threshold predicate
    with no comparator, an interval with no bounds) is a caller bug and raises;
    a *missing or incommensurable operand* is a first-class OPEN verdict, not an
    error. Reject the guessable, escalate the genuinely-open.
    """


# ── comparator dispatch (consumes predicate._COMPARATORS) ─────────────────────

_CMP_FUNCS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}
# Stay locked to the parser's vocabulary — a comparator the parser can emit that
# this table cannot evaluate (or vice versa) is a substrate drift, caught here.
assert set(_CMP_FUNCS) == set(_COMPARATORS), "comparator vocabulary drift vs predicate._COMPARATORS"


# ── normalised quantity ───────────────────────────────────────────────────────

_MONEY = "money"
_DURATION = "duration"
_SCALAR = "scalar"


@dataclass(frozen=True)
class _Q:
    """A quantity reduced to a comparison class, a unit tag, and a magnitude.

    ``magnitude`` is ``None`` only for a calendar-ambiguous duration (one
    carrying months/years) — a signal to open rather than compare. ``unit`` is
    the ISO 4217 currency for money, else ``None``.
    """

    cls: str
    unit: Optional[str]
    magnitude: Optional[Decimal]


def _duration_seconds(d: Duration) -> Optional[Decimal]:
    """Total seconds of the fixed components, or ``None`` when the duration
    carries months/years (no fixed length without an anchor date)."""
    if d.years or d.months:
        return None
    secs = (d.weeks * 7 + d.days) * 86400 + d.hours * 3600 + d.minutes * 60 + d.seconds
    return Decimal(secs)


def _normalise(value: Any) -> Optional[_Q]:
    """Reduce a fact operand (or an interval bound) to a :class:`_Q`, or ``None``
    when it is not a recognised quantity. Floats are rejected outright (the
    ``temporal`` discipline: a quantity that went through binary floating point
    is already wrong)."""
    if isinstance(value, Money):
        return _Q(_MONEY, value.currency, value.amount)
    if isinstance(value, Duration):
        return _Q(_DURATION, None, _duration_seconds(value))
    if isinstance(value, bool):            # bool is an int subclass — never a quantity
        return None
    if isinstance(value, float):           # reject: no binary float in a comparison
        return None
    if isinstance(value, (int, Decimal)):
        return _Q(_SCALAR, None, Decimal(value))
    if isinstance(value, str):
        try:
            return _Q(_SCALAR, None, Decimal(value))
        except InvalidOperation:
            return None
    return None


# Fixed-length time units → seconds, so a threshold stated in a time unit builds a
# DURATION bound comparable with a Duration operand (both reduce to seconds, exactly
# as `_duration_seconds` does). Months/years are calendar-ambiguous (no fixed length
# without an anchor date) → a None magnitude → OPEN, mirroring `_duration_seconds`'
# refusal to invent a month length.
_TIME_UNIT_SECONDS: dict[str, Optional[int]] = {
    "seconds": 1, "minutes": 60, "hours": 3600, "days": 86400, "weeks": 604800,
    "months": None, "years": None,
}


def _time_unit(unit: str) -> Optional[str]:
    """Canonical plural key for a time unit ('hour'→'hours', 'days'→'days'), or
    ``None`` when ``unit`` does not name a time unit."""
    key = unit.lower()
    if not key.endswith("s"):
        key += "s"
    return key if key in _TIME_UNIT_SECONDS else None


def _bound_from_predicate(pred: Predicate) -> _Q:
    """The threshold bound carried by a ``kind='threshold'`` Predicate. The unit
    slot is classified by *trying to build a Money* — a currency code succeeds
    (money bound); a time unit (hours/days/weeks/…) builds a DURATION bound so a
    jurist-natural ``"<= 72 hours"`` compares against a :class:`temporal.Duration`
    operand rather than silently unit-mismatching to OPEN; "%"/None or anything
    else falls through to scalar. This consumes ``temporal.Money``'s ISO 4217 gate
    rather than re-checking it."""
    val = Decimal(pred.value)              # Predicate.__post_init__ guarantees decimal-parseable
    unit = pred.unit
    if unit and unit != "%":
        try:
            Money(amount=val, currency=unit)
            return _Q(_MONEY, unit, val)
        except TemporalError:
            pass                           # not a currency → try time unit, else scalar
        tkey = _time_unit(unit)
        if tkey is not None:
            secs = _TIME_UNIT_SECONDS[tkey]
            # calendar-ambiguous (months/years) → None magnitude → OPEN, like a
            # Duration carrying months/years.
            magnitude = None if secs is None else val * Decimal(secs)
            return _Q(_DURATION, None, magnitude)
    return _Q(_SCALAR, None, val)


def _dimension_of(q: _Q) -> Optional[Dimension]:
    """A duration comparison is temporal reasoning; money/scalar have no
    Dimension member (quantitative is not one of the five)."""
    return Dimension.TEMPORAL if q.cls is _DURATION else None


# ── inputs ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Interval:
    """A membership interval with independently open/closed bounds.

    Either bound may be ``None`` (a half-open ray); at least one must be present.
    A bound may be a :class:`temporal.Money`, a :class:`temporal.Duration`, or a
    plain number — it is normalised the same way the operand is, so a
    unit-mismatched bound opens the condition rather than mis-comparing.
    """

    lower: Any = None
    upper: Any = None
    lower_closed: bool = True
    upper_closed: bool = True

    def __post_init__(self) -> None:
        if self.lower is None and self.upper is None:
            raise QuantError("interval needs at least one bound (both None is not an interval)")


@dataclass(frozen=True)
class QuantCondition:
    """One quantitative antecedent condition. Exactly one mode is set:

      * ``predicate`` — a ``kind='threshold'`` :class:`predicate.Predicate`
        (comparator + value + unit) from :func:`predicate.parse_condition`;
      * ``interval`` — an :class:`Interval` membership test.

    ``subject_ref`` names the fact the operand is looked up by (defaults to the
    predicate's own ``subject_ref``). ``name`` is a human label.
    """

    name: str = ""
    subject_ref: str = ""
    predicate: Optional[Predicate] = None
    interval: Optional[Interval] = None

    def __post_init__(self) -> None:
        if (self.predicate is None) == (self.interval is None):
            raise QuantError("QuantCondition needs exactly one of predicate / interval")
        if self.predicate is not None:
            if self.predicate.kind != "threshold":
                raise QuantError(
                    f"predicate mode needs a kind='threshold' Predicate, got {self.predicate.kind!r}")
            if not self.subject_ref:
                object.__setattr__(self, "subject_ref", self.predicate.subject_ref)

    def label(self) -> str:
        return self.name or self.subject_ref or (
            self.predicate.subject_ref if self.predicate else "interval")


def _coerce_condition(cond: Any) -> QuantCondition:
    """Accept a ready :class:`QuantCondition` or a bare threshold
    :class:`predicate.Predicate` (wrapped for convenience)."""
    if isinstance(cond, QuantCondition):
        return cond
    if isinstance(cond, Predicate):
        return QuantCondition(predicate=cond, subject_ref=cond.subject_ref)
    raise QuantError(f"cond must be a QuantCondition or a threshold Predicate, got {type(cond).__name__}")


# ── operand resolution ────────────────────────────────────────────────────────

_MISSING = object()


def _resolve_operand(cond: QuantCondition, facts: Any) -> Any:
    """The measured fact the condition is read against.

    ``facts`` may be a Mapping keyed by the condition's ``subject_ref`` (or the
    generic ``"operand"`` key), or the operand value itself. An absent key
    yields the ``_MISSING`` sentinel (→ OPEN); a present-but-``None`` value is
    returned as ``None`` (also → OPEN, but distinguishably 'unknown')."""
    if isinstance(facts, Mapping):
        for key in (cond.subject_ref, cond.name, "operand"):
            if key and key in facts:
                return facts[key]
        return _MISSING
    return facts


# ── evaluators ────────────────────────────────────────────────────────────────

def _mismatch_reason(a: _Q, b: _Q) -> str:
    if a.cls != b.cls:
        return f"unit mismatch: operand is {a.cls}, bound is {b.cls} — incomparable → OPEN"
    return f"currency mismatch: operand in {a.unit}, bound in {b.unit} — incomparable → OPEN"


def _commensurable(a: _Q, b: _Q) -> bool:
    if a.cls != b.cls:
        return False
    if a.cls is _MONEY and a.unit != b.unit:
        return False
    return True


def _eval_threshold(cond: QuantCondition, operand: Any, label: str) -> DimVerdict:
    op_q = _normalise(operand)
    bound = _bound_from_predicate(cond.predicate)
    dim = _dimension_of(bound)
    if op_q is None:
        return DimVerdict(label, dim, Verdict.OPEN, evidence=operand,
                          reason=f"operand {operand!r} is not a recognised quantity "
                                 f"(no fabricated comparison) → OPEN")
    if not _commensurable(op_q, bound):
        return DimVerdict(label, _dimension_of(op_q) or dim, Verdict.OPEN,
                          evidence={"operand": op_q, "bound": bound},
                          reason=_mismatch_reason(op_q, bound))
    if op_q.magnitude is None or bound.magnitude is None:
        return DimVerdict(label, Dimension.TEMPORAL, Verdict.OPEN,
                          evidence={"operand": op_q, "bound": bound},
                          reason="calendar-ambiguous duration (months/years carry no fixed "
                                 "length without an anchor date) → OPEN, never guessed")
    comparator = cond.predicate.comparator
    ok = _CMP_FUNCS[comparator](op_q.magnitude, bound.magnitude)
    verdict = Verdict.SATISFIED if ok else Verdict.NOT_SATISFIED
    unit_note = f" {bound.unit}" if bound.unit else ""
    return DimVerdict(label, _dimension_of(op_q), verdict,
                      evidence={"operand": str(op_q.magnitude), "comparator": comparator,
                                "bound": str(bound.magnitude), "unit": bound.unit},
                      reason=f"{op_q.magnitude}{unit_note} {comparator} {bound.magnitude}{unit_note} = {ok}")


def _eval_interval(cond: QuantCondition, operand: Any, label: str) -> DimVerdict:
    interval = cond.interval
    op_q = _normalise(operand)
    if op_q is None:
        return DimVerdict(label, None, Verdict.OPEN, evidence=operand,
                          reason=f"operand {operand!r} is not a recognised quantity → OPEN")
    dim = _dimension_of(op_q)

    # Lower bound: operand must be >= lower (closed) or > lower (open).
    if interval.lower is not None:
        lb = _normalise(interval.lower)
        if lb is None:
            return DimVerdict(label, dim, Verdict.OPEN, reason="lower bound is not a recognised quantity → OPEN")
        if not _commensurable(op_q, lb):
            return DimVerdict(label, _dimension_of(op_q) or dim, Verdict.OPEN,
                              evidence={"operand": op_q, "lower": lb}, reason=_mismatch_reason(op_q, lb))
        if op_q.magnitude is None or lb.magnitude is None:
            return DimVerdict(label, Dimension.TEMPORAL, Verdict.OPEN,
                              reason="calendar-ambiguous duration bound → OPEN")
        below = (op_q.magnitude < lb.magnitude) if interval.lower_closed \
            else (op_q.magnitude <= lb.magnitude)
        if below:
            edge = "[" if interval.lower_closed else "("
            return DimVerdict(label, dim, Verdict.NOT_SATISFIED,
                              evidence={"operand": str(op_q.magnitude), "lower": str(lb.magnitude),
                                        "lower_closed": interval.lower_closed},
                              reason=f"{op_q.magnitude} below lower bound {edge}{lb.magnitude} → outside")

    # Upper bound: operand must be <= upper (closed) or < upper (open).
    if interval.upper is not None:
        ub = _normalise(interval.upper)
        if ub is None:
            return DimVerdict(label, dim, Verdict.OPEN, reason="upper bound is not a recognised quantity → OPEN")
        if not _commensurable(op_q, ub):
            return DimVerdict(label, _dimension_of(op_q) or dim, Verdict.OPEN,
                              evidence={"operand": op_q, "upper": ub}, reason=_mismatch_reason(op_q, ub))
        if op_q.magnitude is None or ub.magnitude is None:
            return DimVerdict(label, Dimension.TEMPORAL, Verdict.OPEN,
                              reason="calendar-ambiguous duration bound → OPEN")
        above = (op_q.magnitude > ub.magnitude) if interval.upper_closed \
            else (op_q.magnitude >= ub.magnitude)
        if above:
            edge = "]" if interval.upper_closed else ")"
            return DimVerdict(label, dim, Verdict.NOT_SATISFIED,
                              evidence={"operand": str(op_q.magnitude), "upper": str(ub.magnitude),
                                        "upper_closed": interval.upper_closed},
                              reason=f"{op_q.magnitude} above upper bound {ub.magnitude}{edge} → outside")

    lo = "[" if interval.lower_closed else "("
    hi = "]" if interval.upper_closed else ")"
    lv = "-∞" if interval.lower is None else str(_normalise(interval.lower).magnitude)
    uv = "+∞" if interval.upper is None else str(_normalise(interval.upper).magnitude)
    return DimVerdict(label, dim, Verdict.SATISFIED,
                      evidence={"operand": str(op_q.magnitude), "interval": f"{lo}{lv}, {uv}{hi}"},
                      reason=f"{op_q.magnitude} ∈ {lo}{lv}, {uv}{hi} → inside")


# ── the op ────────────────────────────────────────────────────────────────────

def evaluate_quantitative(cond: Any, facts: Any) -> DimVerdict:
    """Evaluate ONE quantitative condition against a fact operand, honestly.

    ``cond`` is a :class:`QuantCondition` (threshold or interval mode) or a bare
    ``kind='threshold'`` :class:`predicate.Predicate` (wrapped automatically).
    ``facts`` is either the measured operand itself — a :class:`temporal.Money`,
    a :class:`temporal.Duration`, or a plain number — or a Mapping the operand is
    looked up in by the condition's ``subject_ref`` (falling back to ``name`` and
    the generic ``"operand"`` key).

    Returns a :class:`cross_subsumption.DimVerdict` carrying the SHARED
    :class:`cross_subsumption.Verdict`:

      * **SATISFIED** — the comparison / membership holds;
      * **NOT_SATISFIED** — it is well-typed and commensurable but false
        (closed-world: a real numeric miss, not an absence);
      * **OPEN** — the operand is missing, ``None``, not a recognised quantity,
        unit-incommensurable with the bound, or a calendar-ambiguous duration.
        OPEN is the honest escalate verdict, never a fabricated comparison.

    The result type is exactly ``cross_subsumption``'s per-dimension
    ``DimVerdict``, so it folds into
    :func:`cross_subsumption.subsume_antecedent`'s AND-with-OPEN-dominant
    aggregation unchanged.
    """
    cond = _coerce_condition(cond)
    label = cond.label()

    operand = _resolve_operand(cond, facts)
    if operand is _MISSING:
        return DimVerdict(label, None, Verdict.OPEN, evidence=None,
                          reason=f"no operand for {cond.subject_ref or label!r} in facts "
                                 f"(missing) → OPEN, never a guessed comparison")
    if operand is None:
        return DimVerdict(label, None, Verdict.OPEN, evidence=None,
                          reason=f"operand for {cond.subject_ref or label!r} is unknown (None) "
                                 f"→ OPEN, never guessed")

    if cond.predicate is not None:
        return _eval_threshold(cond, operand, label)
    return _eval_interval(cond, operand, label)
