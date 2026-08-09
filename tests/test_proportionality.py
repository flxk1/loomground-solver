# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Structured proportionality + Alexy Weight Formula (O94–O99) — COMPUTES from
supplied triadic weights; a tie (W==1) or any failed prong returns the shared
relation.ESCALATE sentinel, never a fabricated winner."""
from __future__ import annotations

import pytest

from loomground_solver.relation import ESCALATE
from loomground_solver.proportionality import (
    ESCALATE_OUTCOME,
    I_PREVAILS,
    J_PREVAILS,
    LIGHT,
    MODERATE,
    NECESSITY,
    SERIOUS,
    STRICTO_SENSU,
    TRIAD,
    Alternative,
    PrincipleWeight,
    ProportionalityResult,
    necessity_holds,
    proportionality,
    weight_formula,
)


def _pw(label, i, g, r):
    return PrincipleWeight(label=label, intensity=i, abstract_weight=g, reliability=r)


def test_triadic_scale_is_powers_of_two():
    assert TRIAD == {LIGHT: 1, MODERATE: 2, SERIOUS: 4}


def test_side_i_prevails_when_weight_above_one():
    # i = 4*2*4 = 32 ; j = 1*1*1 = 1 ; W = 32 > 1
    res = proportionality(
        aim="public safety", legitimate=True, suitable=True,
        means_effectiveness=SERIOUS, means_intrusiveness=MODERATE, alternatives=(),
        side_i=_pw("safety", SERIOUS, MODERATE, SERIOUS),
        side_j=_pw("privacy", LIGHT, LIGHT, LIGHT))
    assert res.outcome == I_PREVAILS
    assert res.prevailing == "safety"
    assert res.weight == 32.0
    assert not res.escalated()
    assert res.prong(STRICTO_SENSU).passed is True
    assert isinstance(res, ProportionalityResult)


def test_side_j_prevails_when_weight_below_one():
    # i = 1*1*1 = 1 ; j = 4*2*2 = 16 ; W = 1/16 < 1
    res = proportionality(
        aim="disclosure", legitimate=True, suitable=True,
        means_effectiveness=MODERATE, means_intrusiveness=MODERATE, alternatives=(),
        side_i=_pw("transparency", LIGHT, LIGHT, LIGHT),
        side_j=_pw("privacy", SERIOUS, MODERATE, MODERATE))
    assert res.outcome == J_PREVAILS
    assert res.prevailing == "privacy"
    assert res.weight == pytest.approx(1 / 16)


def test_exact_tie_returns_escalate_never_a_coin_flip():
    # i = 4*1*1 = 4 ; j = 2*2*1 = 4 ; W == 1 exactly -> ESCALATE
    res = proportionality(
        aim="balance", legitimate=True, suitable=True,
        means_effectiveness=MODERATE, means_intrusiveness=MODERATE, alternatives=(),
        side_i=_pw("liberty", SERIOUS, LIGHT, LIGHT),
        side_j=_pw("security", MODERATE, MODERATE, LIGHT))
    assert res.prevailing is ESCALATE           # the shared sentinel, by identity
    assert res.escalated() is True
    assert res.outcome == ESCALATE_OUTCOME
    assert res.weight == 1.0
    assert res.prong(STRICTO_SENSU).passed is False


def test_necessity_fails_when_milder_equally_effective_means_exists():
    # a supplied alternative is equally effective (SERIOUS>=SERIOUS) and less
    # intrusive (LIGHT<SERIOUS): necessity fails -> ESCALATE, balancing not reached
    res = proportionality(
        aim="crowd control", legitimate=True, suitable=True,
        means_effectiveness=SERIOUS, means_intrusiveness=SERIOUS,
        alternatives=(Alternative("cordon", effectiveness=SERIOUS, intrusiveness=LIGHT),),
        side_i=_pw("order", SERIOUS, SERIOUS, SERIOUS),
        side_j=_pw("assembly", LIGHT, LIGHT, LIGHT))
    assert res.escalated() is True
    assert res.prevailing is ESCALATE
    assert res.weight is None                    # stricto sensu never reached
    nec = res.prong(NECESSITY)
    assert nec.passed is False
    assert "cordon" in nec.detail


def test_illegitimate_aim_short_circuits_to_escalate():
    res = proportionality(
        aim="naked animus", legitimate=False, suitable=True,
        means_effectiveness=MODERATE, means_intrusiveness=MODERATE, alternatives=(),
        side_i=_pw("i", SERIOUS, SERIOUS, SERIOUS),
        side_j=_pw("j", LIGHT, LIGHT, LIGHT))
    assert res.escalated() is True
    assert res.prongs[0].passed is False
    assert res.weight is None


def test_weights_are_inputs_unknown_label_is_fail_closed():
    # an unknown triadic weight must raise, never silently default (honesty floor)
    with pytest.raises(ValueError):
        weight_formula(_pw("i", "huge", LIGHT, LIGHT), _pw("j", LIGHT, LIGHT, LIGHT))
    # and the outcome dict never renders ESCALATE as a winner label
    res = proportionality(
        aim="balance", legitimate=True, suitable=True,
        means_effectiveness=MODERATE, means_intrusiveness=MODERATE, alternatives=(),
        side_i=_pw("liberty", SERIOUS, LIGHT, LIGHT),
        side_j=_pw("security", MODERATE, MODERATE, LIGHT))
    assert res.to_dict()["prevailing"] == "ESCALATE"


def test_necessity_holds_when_no_alternative_dominates():
    ok, dominating = necessity_holds(
        MODERATE, LIGHT,
        (Alternative("weaker", effectiveness=LIGHT, intrusiveness=LIGHT),))
    assert ok is True and dominating is None
