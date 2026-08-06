# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Quantitative condition evaluation — branch-level tests.

Every test pins a BRANCH, not just an output: value above / below / exactly at a
threshold under each of the six comparators; inside / outside / on the boundary
of an interval with open vs closed bounds; unit-carrying comparisons (money with
matching and mismatched currency, duration, scalar count); and the honesty
branches — missing operand, unknown (None) operand, unit mismatch, and a
calendar-ambiguous duration — all resolving to the SHARED
:class:`cross_subsumption.Verdict.OPEN`, never a fabricated comparison.
"""
from decimal import Decimal

import pytest

from loomground_solver.quantitative import (
    Interval,
    QuantCondition,
    QuantError,
    evaluate_quantitative,
)
from loomground_solver.predicate import Predicate, parse_condition
from loomground_solver.cross_subsumption import (
    Condition,
    DimVerdict,
    FactSpace,
    Verdict,
    subsume_antecedent,
)
from loomground_solver.dimensions import Dimension
from loomground_solver.temporal import Duration, Money


def _threshold(comparator, value, unit=None, subject="amount"):
    return QuantCondition(
        predicate=Predicate(kind="threshold", subject_ref=subject,
                            comparator=comparator, value=value, unit=unit, confidence=0.9))


# ── threshold: the six comparators, above / at / below ────────────────────────

def test_gt_above_satisfied():
    v = evaluate_quantitative(_threshold(">", "100"), Decimal("150"))
    assert v.verdict is Verdict.SATISFIED


def test_gt_at_boundary_not_satisfied():
    # strictly greater: exactly-at is NOT satisfied (this is the boundary branch)
    v = evaluate_quantitative(_threshold(">", "100"), Decimal("100"))
    assert v.verdict is Verdict.NOT_SATISFIED


def test_gt_below_not_satisfied():
    v = evaluate_quantitative(_threshold(">", "100"), Decimal("50"))
    assert v.verdict is Verdict.NOT_SATISFIED


def test_ge_at_boundary_satisfied():
    # >= includes the endpoint — the branch that separates >= from >
    v = evaluate_quantitative(_threshold(">=", "100"), Decimal("100"))
    assert v.verdict is Verdict.SATISFIED


def test_lt_below_satisfied_and_at_not():
    assert evaluate_quantitative(_threshold("<", "100"), Decimal("99")).verdict is Verdict.SATISFIED
    assert evaluate_quantitative(_threshold("<", "100"), Decimal("100")).verdict is Verdict.NOT_SATISFIED


def test_le_at_boundary_satisfied():
    assert evaluate_quantitative(_threshold("<=", "100"), Decimal("100")).verdict is Verdict.SATISFIED
    assert evaluate_quantitative(_threshold("<=", "100"), Decimal("101")).verdict is Verdict.NOT_SATISFIED


def test_eq_exact_and_off():
    assert evaluate_quantitative(_threshold("==", "42"), Decimal("42")).verdict is Verdict.SATISFIED
    assert evaluate_quantitative(_threshold("==", "42"), Decimal("43")).verdict is Verdict.NOT_SATISFIED


def test_ne_differs_and_equal():
    assert evaluate_quantitative(_threshold("!=", "42"), Decimal("7")).verdict is Verdict.SATISFIED
    assert evaluate_quantitative(_threshold("!=", "42"), Decimal("42")).verdict is Verdict.NOT_SATISFIED


# ── unit-carrying: money ──────────────────────────────────────────────────────

def test_money_matching_currency_compares():
    cond = _threshold(">", "10000", unit="EUR")
    v = evaluate_quantitative(cond, Money(amount=Decimal("15000"), currency="EUR"))
    assert v.verdict is Verdict.SATISFIED
    v2 = evaluate_quantitative(cond, Money(amount=Decimal("9000"), currency="EUR"))
    assert v2.verdict is Verdict.NOT_SATISFIED


def test_money_currency_mismatch_open():
    # EUR threshold vs a USD operand — incommensurable, never silently compared
    cond = _threshold(">", "10000", unit="EUR")
    v = evaluate_quantitative(cond, Money(amount=Decimal("15000"), currency="USD"))
    assert v.verdict is Verdict.OPEN
    assert "currency mismatch" in v.reason


def test_money_bound_vs_scalar_operand_open():
    # a currency-carrying bound vs a bare number is a unit mismatch → OPEN
    cond = _threshold(">", "10000", unit="EUR")
    v = evaluate_quantitative(cond, Decimal("15000"))
    assert v.verdict is Verdict.OPEN
    assert "unit mismatch" in v.reason


# ── unit-carrying: duration ───────────────────────────────────────────────────

def test_duration_compares_when_commensurable():
    # bound and operand both durations of fixed length → real comparison
    interval_cond = QuantCondition(name="delay",
                                   interval=Interval(lower=Duration(days=20), upper=Duration(days=40)))
    inside = evaluate_quantitative(interval_cond, Duration(days=30))
    assert inside.verdict is Verdict.SATISFIED
    assert inside.dimension is Dimension.TEMPORAL       # duration → temporal reasoning
    outside = evaluate_quantitative(interval_cond, Duration(days=10))
    assert outside.verdict is Verdict.NOT_SATISFIED


def test_duration_calendar_ambiguous_open():
    # a month-carrying duration has no fixed length without an anchor → OPEN
    cond = QuantCondition(name="delay", interval=Interval(lower=Duration(days=20), upper=Duration(days=40)))
    v = evaluate_quantitative(cond, Duration(months=1))
    assert v.verdict is Verdict.OPEN
    assert "calendar-ambiguous" in v.reason


def test_duration_vs_scalar_mismatch_open():
    cond = QuantCondition(name="delay", interval=Interval(lower=Duration(days=20)))
    v = evaluate_quantitative(cond, Decimal("30"))
    assert v.verdict is Verdict.OPEN
    assert "unit mismatch" in v.reason


# ── interval membership: open vs closed bounds, boundary branch ───────────────

def _closed(lo, hi):
    return QuantCondition(name="range", interval=Interval(lower=Decimal(lo), upper=Decimal(hi),
                                                          lower_closed=True, upper_closed=True))


def _open(lo, hi):
    return QuantCondition(name="range", interval=Interval(lower=Decimal(lo), upper=Decimal(hi),
                                                         lower_closed=False, upper_closed=False))


def test_interval_inside():
    assert evaluate_quantitative(_closed("5", "20"), Decimal("12")).verdict is Verdict.SATISFIED


def test_interval_outside_below_and_above():
    assert evaluate_quantitative(_closed("5", "20"), Decimal("4")).verdict is Verdict.NOT_SATISFIED
    assert evaluate_quantitative(_closed("5", "20"), Decimal("21")).verdict is Verdict.NOT_SATISFIED


def test_interval_closed_boundary_included():
    # on the boundary of a CLOSED interval → inside
    assert evaluate_quantitative(_closed("5", "20"), Decimal("5")).verdict is Verdict.SATISFIED
    assert evaluate_quantitative(_closed("5", "20"), Decimal("20")).verdict is Verdict.SATISFIED


def test_interval_open_boundary_excluded():
    # same boundary points on an OPEN interval → outside (the open-vs-closed branch)
    lo = evaluate_quantitative(_open("5", "20"), Decimal("5"))
    hi = evaluate_quantitative(_open("5", "20"), Decimal("20"))
    assert lo.verdict is Verdict.NOT_SATISFIED
    assert hi.verdict is Verdict.NOT_SATISFIED
    # strictly interior still passes an open interval
    assert evaluate_quantitative(_open("5", "20"), Decimal("6")).verdict is Verdict.SATISFIED


def test_interval_half_open_ray_lower_only():
    cond = QuantCondition(name="min", interval=Interval(lower=Decimal("100"), lower_closed=True))
    assert evaluate_quantitative(cond, Decimal("100")).verdict is Verdict.SATISFIED
    assert evaluate_quantitative(cond, Decimal("99")).verdict is Verdict.NOT_SATISFIED


def test_interval_half_open_ray_upper_only():
    cond = QuantCondition(name="max", interval=Interval(upper=Decimal("100"), upper_closed=False))
    assert evaluate_quantitative(cond, Decimal("99")).verdict is Verdict.SATISFIED
    assert evaluate_quantitative(cond, Decimal("100")).verdict is Verdict.NOT_SATISFIED


def test_interval_money_currency_mismatch_open():
    cond = QuantCondition(name="band",
                          interval=Interval(lower=Money(amount=Decimal("100"), currency="EUR"),
                                            upper=Money(amount=Decimal("500"), currency="EUR")))
    v = evaluate_quantitative(cond, Money(amount=Decimal("300"), currency="USD"))
    assert v.verdict is Verdict.OPEN


# ── honesty: missing / unknown operand → OPEN ─────────────────────────────────

def test_missing_operand_key_open():
    # Mapping lookup by subject_ref; the key is absent → OPEN (missing), never guessed
    cond = _threshold(">", "100", subject="amount")
    v = evaluate_quantitative(cond, {"something_else": Decimal("5")})
    assert v.verdict is Verdict.OPEN
    assert "missing" in v.reason


def test_none_operand_open():
    cond = _threshold(">", "100", subject="amount")
    v = evaluate_quantitative(cond, {"amount": None})
    assert v.verdict is Verdict.OPEN
    assert "unknown" in v.reason


def test_direct_none_operand_open():
    v = evaluate_quantitative(_threshold(">", "100"), None)
    assert v.verdict is Verdict.OPEN


def test_unrecognised_operand_open():
    # a non-quantity operand is not coerced into a number → OPEN
    v = evaluate_quantitative(_threshold(">", "100"), object())
    assert v.verdict is Verdict.OPEN


def test_float_operand_rejected_open():
    # floats are refused (temporal discipline) rather than silently compared
    v = evaluate_quantitative(_threshold(">", "100"), 150.0)
    assert v.verdict is Verdict.OPEN


# ── mapping resolution by subject_ref ─────────────────────────────────────────

def test_operand_resolved_from_mapping_by_subject_ref():
    cond = _threshold(">", "100", subject="amount")
    v = evaluate_quantitative(cond, {"amount": Decimal("150")})
    assert v.verdict is Verdict.SATISFIED


# ── end-to-end: parse_condition → evaluate ────────────────────────────────────

def test_parsed_predicate_drives_evaluation():
    pred = parse_condition("exceeds EUR 10,000")
    assert pred is not None and pred.kind == "threshold"
    # bare Predicate is accepted directly (wrapped internally)
    v = evaluate_quantitative(pred, Money(amount=Decimal("12000"), currency="EUR"))
    assert v.verdict is Verdict.SATISFIED
    v2 = evaluate_quantitative(pred, Money(amount=Decimal("8000"), currency="EUR"))
    assert v2.verdict is Verdict.NOT_SATISFIED


# ── seam: result folds into subsume_antecedent aggregation ────────────────────

def test_result_type_is_shared_dimverdict():
    v = evaluate_quantitative(_threshold(">", "100"), Decimal("150"))
    assert isinstance(v, DimVerdict)
    assert isinstance(v.verdict, Verdict)


def test_open_quantitative_dominates_antecedent_when_manually_folded():
    # A human folds the quantitative DimVerdict beside a native structural verdict.
    # An OPEN quantitative condition must make the AND OPEN (escalate-dominant),
    # exactly like any native OPEN condition — mirroring subsume_antecedent's rule.
    quant_open = evaluate_quantitative(_threshold(">", "100"), None)  # missing → OPEN
    assert quant_open.verdict is Verdict.OPEN

    # A satisfied native condition on its own would be SATISFIED …
    native = subsume_antecedent(
        [Condition(name="lit", dimension=Dimension.INTENTIONAL, literal="x")],
        FactSpace(literals=frozenset({"x"})))
    assert native.verdict is Verdict.SATISFIED

    # … but folding the OPEN quantitative verdict in flips the aggregate to OPEN.
    folded = [*native.conditions, quant_open]
    opens = [d for d in folded if d.verdict is Verdict.OPEN]
    assert opens, "an OPEN quantitative condition must dominate the AND"


# ── construction guards ───────────────────────────────────────────────────────

def test_condition_needs_exactly_one_mode():
    with pytest.raises(QuantError):
        QuantCondition()                                    # neither
    with pytest.raises(QuantError):
        QuantCondition(predicate=Predicate(kind="threshold", comparator=">", value="1"),
                       interval=Interval(lower=Decimal("0")))   # both


def test_predicate_mode_requires_threshold_kind():
    with pytest.raises(QuantError):
        QuantCondition(predicate=Predicate(kind="state", subject_ref="x"))


def test_interval_needs_a_bound():
    with pytest.raises(QuantError):
        Interval()


# ── time-unit threshold bound: "<= 72 hours" compares against a Duration ───────
# Regression for the false-OPEN found in the GDPR end-to-end run: a threshold
# stated in a time unit must build a DURATION bound (not a scalar), so the
# jurist-natural phrasing compares against a Duration operand instead of
# unit-mismatching to OPEN.

def test_time_unit_threshold_within_deadline_satisfied():
    v = evaluate_quantitative(_threshold("<=", "72", unit="hours"), Duration(hours=48))
    assert v.verdict is Verdict.SATISFIED
    assert v.dimension is Dimension.TEMPORAL


def test_time_unit_threshold_past_deadline_not_satisfied():
    v = evaluate_quantitative(_threshold("<=", "72", unit="hours"), Duration(hours=96))
    assert v.verdict is Verdict.NOT_SATISFIED


def test_time_unit_threshold_singular_unit_normalised():
    # 'hour' (singular) must be recognised exactly like 'hours'.
    v = evaluate_quantitative(_threshold(">=", "1", unit="hour"), Duration(minutes=90))
    assert v.verdict is Verdict.SATISFIED


def test_time_unit_threshold_days_and_weeks_commensurable():
    # a bound in days vs an operand in weeks reduce to the same seconds base.
    v = evaluate_quantitative(_threshold("<", "10", unit="days"), Duration(weeks=1))
    assert v.verdict is Verdict.SATISFIED   # 7 days < 10 days


def test_calendar_ambiguous_bound_unit_opens():
    # a bound of 'months' has no fixed length without an anchor → OPEN, never guessed.
    v = evaluate_quantitative(_threshold("<=", "1", unit="months"), Duration(days=20))
    assert v.verdict is Verdict.OPEN


def test_time_unit_bound_vs_scalar_operand_still_mismatches():
    # honesty preserved: a duration bound vs a bare scalar count is incommensurable.
    v = evaluate_quantitative(_threshold("<=", "72", unit="hours"), Decimal("48"))
    assert v.verdict is Verdict.OPEN
