# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Tests for deontic permissive/prohibitive closure with polarity (O140).

Closure consumes the scenario resolver (never re-deriving collisions) and the
deontic O/P/F vocabulary, adding the residual-default polarity (PRIVATE liberty /
PUBLIC competence) and the strong/weak marking of a permission.
"""
from __future__ import annotations

from loomground_solver.closure import (
    AgentMode, ClosureResult, STRONG, WEAK, close, is_strong_permission,
    verdict_to_operator,
)
from loomground_solver.rulepacks import GENERIC_PACK
from loomground_solver.scenario import Norm
from deontic.operators import (
    OP_OBLIGATION, OP_PERMISSION, OP_PROHIBITION, VALID_OPERATORS, gloss,
)


# ── the six grounded spec cases ──────────────────────────────────────────────

def test_private_empty_is_weak_residual_permission():
    r = close("walk", [], mode=AgentMode.PRIVATE)
    assert r.verdict == "permitted"
    assert r.operator == OP_PERMISSION
    assert r.residual is True
    assert r.fired is False
    assert r.permission_strength == WEAK
    assert r.open is False


def test_public_empty_is_residual_prohibition():
    r = close("walk", [], mode=AgentMode.PUBLIC)
    assert r.verdict == "prohibited"
    assert r.operator == OP_PROHIBITION
    assert r.residual is True
    assert r.fired is False
    assert r.permission_strength is None
    assert r.open is False


def test_express_permission_fires_even_in_public_mode():
    r = close("share", [Norm("share", "permitted", source="art6")],
              mode=AgentMode.PUBLIC)
    assert r.fired is True
    assert r.residual is False
    assert r.verdict == "permitted"
    assert r.permission_strength == STRONG
    assert is_strong_permission(r) is True


def test_express_prohibition_overrides_private_default():
    r = close("disclose", [Norm("disclose", "prohibited", source="nda")],
              mode=AgentMode.PRIVATE)
    assert r.verdict == "prohibited"
    assert r.operator == OP_PROHIBITION
    assert r.fired is True
    assert r.permission_strength is None


def test_genuine_collision_escalates_no_forced_closure():
    r = close("act",
              [Norm("act", "obligatory", source="n1"),
               Norm("act", "prohibited", source="n2")],
              mode=AgentMode.PRIVATE, pack=GENERIC_PACK)
    assert r.open is True
    assert r.verdict is None
    assert r.operator == ""
    assert r.residual is False


def test_express_obligation_is_a_firing_not_a_permission():
    r = close("erase", [Norm("erase", "obligatory", source="gdpr17")],
              mode=AgentMode.PUBLIC)
    assert r.verdict == "obligatory"
    assert r.operator == OP_OBLIGATION
    assert r.fired is True
    assert r.permission_strength is None
    assert r.operator in VALID_OPERATORS


# ── verdict_to_operator: built from deontic constants + gloss ─────────────────

def test_verdict_to_operator_maps_all_three_modalities():
    assert verdict_to_operator("obligatory") == OP_OBLIGATION
    assert verdict_to_operator("permitted") == OP_PERMISSION
    # bridges the 'prohibited' (scenario) / 'forbidden' (deontic gloss) gap
    assert verdict_to_operator("prohibited") == OP_PROHIBITION


def test_verdict_to_operator_empty_for_none_or_unknown():
    assert verdict_to_operator(None) == ""
    assert verdict_to_operator("") == ""
    assert verdict_to_operator("nonsense") == ""


def test_verdict_to_operator_bridges_via_gloss_not_hardcoded():
    # the prohibition branch must agree with the deontic gloss of OP_PROHIBITION
    assert gloss(OP_PROHIBITION) == "forbidden"
    assert verdict_to_operator("prohibited") == OP_PROHIBITION


# ── strong vs weak permission ────────────────────────────────────────────────

def test_weak_residual_permission_is_not_strong():
    r = close("wander", [], mode=AgentMode.PRIVATE)
    assert r.verdict == "permitted"
    assert r.permission_strength == WEAK
    assert is_strong_permission(r) is False


def test_public_residual_prohibition_is_not_a_permission():
    r = close("wander", [], mode=AgentMode.PUBLIC)
    assert is_strong_permission(r) is False


# ── gloss/operator wiring on the result ──────────────────────────────────────

def test_result_gloss_tracks_operator():
    r = close("share", [Norm("share", "permitted", source="p")],
              mode=AgentMode.PRIVATE)
    assert r.gloss == gloss(r.operator)
    assert r.gloss == "permitted"


def test_open_result_has_empty_operator_and_gloss():
    r = close("act",
              [Norm("act", "obligatory", source="a"),
               Norm("act", "prohibited", source="b")],
              mode=AgentMode.PRIVATE)
    assert r.open is True
    assert r.operator == ""
    assert r.gloss == ""
    assert is_strong_permission(r) is False


# ── survivors surface through on a firing ─────────────────────────────────────

def test_fired_result_carries_surviving_source():
    r = close("erase", [Norm("erase", "obligatory", source="gdpr17")],
              mode=AgentMode.PUBLIC)
    assert "gdpr17" in r.survivors


def test_norms_for_other_acts_are_ignored():
    # an obligation on a different act must not disturb the closure of 'walk'
    r = close("walk", [Norm("run", "prohibited", source="x")],
              mode=AgentMode.PRIVATE)
    assert r.verdict == "permitted"
    assert r.residual is True
    assert r.fired is False


# ── to_dict is faithful ──────────────────────────────────────────────────────

def test_to_dict_roundtrips_fields():
    r = close("share", [Norm("share", "permitted", source="art6")],
              mode=AgentMode.PUBLIC)
    d = r.to_dict()
    assert d["act"] == "share"
    assert d["verdict"] == "permitted"
    assert d["operator"] == OP_PERMISSION
    assert d["permission_strength"] == STRONG
    assert d["mode"] == "public"
    assert d["survivors"] == ["art6"]
    assert d["open"] is False


def test_result_is_frozen():
    r = close("walk", [], mode=AgentMode.PRIVATE)
    assert isinstance(r, ClosureResult)
    try:
        r.verdict = "prohibited"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("ClosureResult should be frozen")
