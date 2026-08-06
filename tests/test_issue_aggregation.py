# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Deterministic tests for issue_aggregation.aggregate_issues.

Every case pins fixed sub-issue verdicts and asserts a fixed overall verdict —
no model, no randomness. The op only AGGREGATES upstream verdicts; these tests
never exercise the per-issue evaluators.
"""

import dataclasses

import pytest

from loomground_solver.cross_subsumption import (
    AntecedentVerdict,
    DimVerdict,
    Verdict,
)
from loomground_solver.issue_aggregation import (
    IssueAggregate,
    aggregate_issues,
)

S = Verdict.SATISFIED
N = Verdict.NOT_SATISFIED
O = Verdict.OPEN


def test_all_satisfied_is_satisfied_and_carries_every_subissue():
    res = aggregate_issues([("exists", S), ("not_perished", S), ("enforceable", S)])
    assert res.overall is S
    assert res.satisfied is True
    assert res.open is False
    # every sub-issue verdict carried, in order
    assert res.issues == (("exists", S), ("not_perished", S), ("enforceable", S))


def test_one_open_among_satisfied_dominates():
    res = aggregate_issues([("exists", S), ("not_perished", O), ("enforceable", S)])
    assert res.overall is O
    assert res.open is True
    assert res.satisfied is False
    # never fabricated to SATISFIED despite the two satisfied siblings
    assert res.issues == (("exists", S), ("not_perished", O), ("enforceable", S))


def test_open_dominates_a_not_satisfied_sibling():
    # unordered fold: OPEN must win over NOT_SATISFIED — never NOT_SATISFIED,
    # never a fabricated SATISFIED.
    res = aggregate_issues([("exists", N), ("deadline", O)])
    assert res.overall is O
    assert res.overall is not N
    assert res.overall is not S


def test_one_not_satisfied_none_open_is_not_satisfied():
    res = aggregate_issues([("exists", S), ("not_perished", N), ("enforceable", S)])
    assert res.overall is N
    assert res.satisfied is False
    assert res.open is False


def test_mixed_all_three_open_still_dominates():
    res = aggregate_issues([("a", S), ("b", N), ("c", O), ("d", S)])
    assert res.overall is O


def test_ordered_shortcircuit_blocks_first_later_open_never_reached():
    inp = [("exists", N), ("deadline", O)]
    ordered = aggregate_issues(inp, order=["exists", "deadline"])
    # exists fails first; the later OPEN issue is never reached
    assert ordered.overall is N
    assert ordered.issues == (("exists", N),)  # only reached prefix carried
    # contrast: the SAME input unordered escalates to OPEN
    unordered = aggregate_issues(inp)
    assert unordered.overall is O


def test_ordered_reaches_later_only_if_earlier_satisfied():
    res = aggregate_issues(
        [("exists", S), ("deadline", O), ("enforceable", S)],
        order=["exists", "deadline", "enforceable"],
    )
    # earlier SATISFIED, so deadline is reached; it is OPEN → OPEN
    assert res.overall is O
    # reached prefix: exists + deadline, but NOT enforceable (never reached)
    assert res.issues == (("exists", S), ("deadline", O))


def test_ordered_all_satisfied_reaches_all():
    res = aggregate_issues(
        [("a", S), ("b", S), ("c", S)],
        order=["a", "b", "c"],
    )
    assert res.overall is S
    assert res.issues == (("a", S), ("b", S), ("c", S))


def test_empty_is_vacuously_satisfied_unordered_and_ordered():
    assert aggregate_issues([]).overall is S
    assert aggregate_issues([]).issues == ()
    assert aggregate_issues([("a", N)], order=[]).overall is S
    assert aggregate_issues([("a", N)], order=[]).issues == ()


def test_accepts_antecedent_and_dim_verdict_wrappers():
    ant = AntecedentVerdict(Verdict.SATISFIED, conditions=(), reason="")
    dim = DimVerdict("c", None, Verdict.OPEN)
    res = aggregate_issues([("claim", ant), ("element", dim)])
    # ant coerces to SATISFIED, dim to OPEN → OPEN dominates
    assert res.overall is O
    # carried verdicts are the coerced bare Verdicts
    assert res.issues == (("claim", S), ("element", O))


def test_wrapper_all_satisfied():
    ant1 = AntecedentVerdict(Verdict.SATISFIED, conditions=(), reason="")
    dim1 = DimVerdict("c", None, Verdict.SATISFIED)
    res = aggregate_issues([("claim", ant1), ("element", dim1)])
    assert res.overall is S


def test_bad_verdict_type_raises_typeerror():
    with pytest.raises(TypeError):
        aggregate_issues([("bad", "satisfied")])
    with pytest.raises(TypeError):
        aggregate_issues([("bad", None)])
    with pytest.raises(TypeError):
        aggregate_issues([("bad", 1)])


def test_result_is_frozen_immutable():
    res = aggregate_issues([("a", S)])
    assert isinstance(res, IssueAggregate)
    with pytest.raises(dataclasses.FrozenInstanceError):
        res.overall = N  # type: ignore[misc]


def test_ordered_name_not_in_issues_is_skipped():
    res = aggregate_issues(
        [("a", S), ("c", S)],
        order=["a", "b", "c"],  # "b" absent from issues
    )
    assert res.overall is S
    assert res.issues == (("a", S), ("c", S))
