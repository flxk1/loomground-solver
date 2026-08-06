# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Distribution measurement (Family T, O148 + O152) — MEASURE ONLY: inequality
metrics and the four-fifths adverse-impact ratio flag escalation, never a
verdict."""
from __future__ import annotations

from loomground_solver.consistency import DecidedCase
from loomground_solver.distribution import (
    FOUR_FIFTHS,
    ImpactRatio,
    InequalityMetrics,
    adverse_impact,
    inequality,
    rates_from_cases,
)


# ── O148: inequality ─────────────────────────────────────────────────────────

def test_perfect_equality_has_zero_gini():
    m = inequality([10, 10, 10])
    assert m.gini == 0.0
    assert m.range == 0.0
    assert m.ratio == 1.0
    assert m.minimum == 10
    assert m.maximum == 10
    assert m.total == 30
    assert m.n == 3


def test_gini_hand_checked():
    # 2*Σi*x_i = 2*(1*1+2*2+3*3+4*4) = 2*30 = 60; n*Σx = 4*10 = 40;
    # (n+1)/n = 1.25 ; G = 60/40 - 1.25 = 1.5 - 1.25 = 0.25
    m = inequality([1, 2, 3, 4])
    assert m.gini == 0.25


def test_range_and_ratio():
    m = inequality([2, 8])
    assert m.range == 6.0
    assert m.ratio == 4.0
    assert m.minimum == 2
    assert m.maximum == 8


def test_single_element_is_vacuous():
    m = inequality([5])
    assert m.gini == 0.0
    assert m.ratio == 1.0
    assert m.range == 0.0
    assert m.n == 1


def test_empty_is_vacuous():
    m = inequality([])
    assert m.gini == 0.0
    assert m.ratio == 1.0
    assert m.range == 0.0
    assert m.total == 0.0
    assert m.n == 0


def test_zero_min_positive_max_ratio_is_inf():
    m = inequality([0, 5])
    assert m.ratio == float("inf")
    assert m.range == 5.0


def test_all_zero_holdings_ratio_is_one_and_gini_zero():
    m = inequality([0, 0, 0])
    assert m.ratio == 1.0
    assert m.gini == 0.0
    assert m.total == 0.0


def test_inequality_unsorted_input_is_order_independent():
    assert inequality([4, 1, 3, 2]).gini == inequality([1, 2, 3, 4]).gini == 0.25


# ── O152: adverse_impact ─────────────────────────────────────────────────────

def test_ratio_above_threshold_does_not_breach():
    r = adverse_impact({"A": (50, 100), "B": (45, 100)})
    assert r.rates == {"A": 0.5, "B": 0.45}
    assert r.reference_group == "A"
    assert r.reference_rate == 0.5
    assert r.ratio == 0.9
    assert r.breaches is False
    assert r.flagged_pairs == ()
    assert r.threshold == FOUR_FIFTHS


def test_ratio_below_threshold_breaches_and_flags():
    r = adverse_impact({"A": (60, 100), "B": (30, 100)})
    assert r.ratio == 0.5
    assert r.breaches is True
    assert r.disadvantaged_group == "B"
    assert r.lowest_rate == 0.3
    assert ("B", 0.5) in r.flagged_pairs


def test_measure_only_boundary_no_verdict_key():
    r = adverse_impact({"A": (60, 100), "B": (30, 100)})
    d = r.to_dict()
    assert "verdict" not in d
    assert "discriminatory" not in d
    assert "unlawful" not in d
    assert "unjust" not in d
    # only metrics / flags are exposed
    assert set(d) == {
        "rates", "reference_group", "reference_rate", "disadvantaged_group",
        "lowest_rate", "ratio", "threshold", "breaches", "flagged_pairs",
    }


def test_groups_with_zero_total_are_skipped():
    r = adverse_impact({"A": (50, 100), "B": (0, 0)})
    assert "B" not in r.rates
    assert r.rates == {"A": 0.5}


def test_single_group_does_not_breach():
    r = adverse_impact({"A": (3, 10)})
    assert r.ratio == 1.0
    assert r.breaches is False
    assert r.flagged_pairs == ()
    assert r.reference_group == "A"
    assert r.disadvantaged_group == "A"


def test_all_zero_rate_groups_no_disparity():
    r = adverse_impact({"A": (0, 10), "B": (0, 10)})
    assert r.reference_rate == 0.0
    assert r.ratio == 1.0
    assert r.breaches is False
    assert r.flagged_pairs == ()


def test_custom_threshold_is_honoured():
    r = adverse_impact({"A": (100, 100), "B": (85, 100)}, threshold=0.9)
    assert r.ratio == 0.85
    assert r.breaches is True
    assert ("B", 0.85) in r.flagged_pairs


def test_no_groups_at_all_is_vacuous():
    r = adverse_impact({})
    assert r.rates == {}
    assert r.ratio == 1.0
    assert r.breaches is False
    assert r.flagged_pairs == ()


# ── consuming DecidedCase via rates_from_cases ───────────────────────────────

def test_rates_from_cases_buckets_by_group_key():
    cases = [
        DecidedCase("c1", {"gender": "f"}, "reject"),
        DecidedCase("c2", {"gender": "f"}, "reject"),
        DecidedCase("c3", {"gender": "m"}, "hire"),
        DecidedCase("c4", {"gender": "m"}, "reject"),
    ]
    counts = rates_from_cases(cases, group_key="gender", favourable={"hire"})
    assert counts == {"f": (0, 2), "m": (1, 2)}

    r = adverse_impact(counts)
    assert r.rates["f"] == 0.0
    assert r.rates["m"] == 0.5
    assert r.ratio == 0.0
    assert r.breaches is True
    assert r.disadvantaged_group == "f"


def test_rates_from_cases_accepts_a_predicate():
    cases = [
        DecidedCase("c1", {"g": "x"}, "grant"),
        DecidedCase("c2", {"g": "x"}, "deny"),
        DecidedCase("c3", {"g": "y"}, "grant"),
    ]
    counts = rates_from_cases(
        cases, group_key="g", favourable=lambda o: o == "grant")
    assert counts == {"x": (1, 2), "y": (1, 1)}


def test_rates_from_cases_skips_cases_missing_group_key():
    cases = [
        DecidedCase("c1", {"g": "x"}, "hire"),
        DecidedCase("c2", {"other": "z"}, "hire"),
    ]
    counts = rates_from_cases(cases, group_key="g", favourable={"hire"})
    assert counts == {"x": (1, 1)}


# ── frozen / metric-only shape ───────────────────────────────────────────────

def test_dataclasses_are_frozen():
    import dataclasses
    import pytest

    m = inequality([1, 2, 3])
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.gini = 0.9  # type: ignore[misc]

    r = adverse_impact({"A": (1, 2)})
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.ratio = 0.1  # type: ignore[misc]


def test_inequality_to_dict_exposes_only_metrics():
    d = inequality([1, 2, 3]).to_dict()
    assert set(d) == {"gini", "range", "ratio", "minimum", "maximum",
                      "total", "n"}
    assert "unequal" not in d
    assert "unjust" not in d


def test_types_are_the_expected_dataclasses():
    assert isinstance(inequality([1]), InequalityMetrics)
    assert isinstance(adverse_impact({"A": (1, 2)}), ImpactRatio)
