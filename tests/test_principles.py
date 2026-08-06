# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Collision-of-principles detection + rule/principle routing (O93) — it detects
the clash (via rulepacks.contradicts) and routes it (rule → lex-ordering,
principle → balancing); it never resolves the collision."""
from __future__ import annotations

import pytest

from loomground_solver.principles import (
    NO_COLLISION,
    PRINCIPLE,
    PRINCIPLE_COLLISION,
    ROUTE_BALANCING,
    ROUTE_LEX_ORDERING,
    ROUTE_NONE,
    RULE,
    RULE_COLLISION,
    CollisionRouting,
    classify_collision,
    route_for,
)
from loomground_solver.scenario import Norm


def _n(deontic: str, act: str = "disclose", source: str = "s") -> Norm:
    return Norm(act=act, deontic=deontic, source=source)


def test_two_contradicting_rules_route_to_lex_ordering():
    r = classify_collision(_n("obligatory"), _n("prohibited"),
                           character_a=RULE, character_b=RULE)
    assert r.collides is True
    assert r.kind == RULE_COLLISION
    assert r.route == ROUTE_LEX_ORDERING
    assert route_for(r) == ROUTE_LEX_ORDERING
    assert isinstance(r, CollisionRouting)


def test_rule_versus_principle_routes_to_balancing():
    r = classify_collision(_n("obligatory"), _n("prohibited"),
                           character_a=RULE, character_b=PRINCIPLE)
    assert r.kind == PRINCIPLE_COLLISION
    assert r.route == ROUTE_BALANCING
    assert route_for(r) == ROUTE_BALANCING


def test_two_principles_route_to_balancing():
    r = classify_collision(_n("permitted"), _n("prohibited"),
                           character_a=PRINCIPLE, character_b=PRINCIPLE)
    assert r.kind == PRINCIPLE_COLLISION
    assert r.route == ROUTE_BALANCING


def test_non_contradicting_modals_are_no_collision():
    # obligatory + permitted do not clash (rulepacks.contradicts is False)
    r = classify_collision(_n("obligatory"), _n("permitted"),
                           character_a=RULE, character_b=PRINCIPLE)
    assert r.collides is False
    assert r.kind == NO_COLLISION
    assert r.route == ROUTE_NONE
    assert route_for(r) is None


def test_different_acts_are_a_construction_error():
    with pytest.raises(ValueError):
        classify_collision(_n("obligatory", act="disclose"),
                           _n("prohibited", act="retain"),
                           character_a=RULE, character_b=RULE)


def test_unknown_character_is_fail_closed_never_inferred():
    with pytest.raises(ValueError):
        classify_collision(_n("obligatory"), _n("prohibited"),
                           character_a="policy", character_b=RULE)


def test_routing_records_no_verdict():
    # it ROUTES; it does not resolve — no winner/verdict key may appear
    r = classify_collision(_n("obligatory"), _n("prohibited"),
                           character_a=RULE, character_b=RULE)
    d = r.to_dict()
    for banned in ("winner", "verdict", "resolution", "prevailing", "loser"):
        assert banned not in d
    assert d["route"] == ROUTE_LEX_ORDERING
    assert d["characters"] == [RULE, RULE]
