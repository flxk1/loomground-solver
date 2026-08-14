# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Tests for the typed-relation composition algebra (loomground_solver.relation).

Two jobs: exercise the generic mechanism (validation, compose, left-fold,
escalation, inverse, dimension), and prove — with a legal-shaped table — that it
reproduces the behaviour of the domain algebra it replaces (host's
``legal_connection``), so moving the engine into the solver is behaviour-
preserving and only the *data* stays in the domain plane.
"""
from __future__ import annotations

import pytest

from loomground_solver.dimensions import Dimension
from loomground_solver.relation import ESCALATE, RelationAlgebra


# ── construction / validation ─────────────────────────────────────

def test_rejects_table_key_outside_vocabulary():
    with pytest.raises(ValueError, match="unknown relation"):
        RelationAlgebra(vocabulary={"a", "b"}, table={("a", "typo"): "b"})


def test_rejects_table_value_outside_vocabulary():
    with pytest.raises(ValueError, match="unknown relation"):
        RelationAlgebra(vocabulary={"a", "b"}, table={("a", "b"): "ghost"})


def test_rejects_inverse_and_dimension_outside_vocabulary():
    with pytest.raises(ValueError, match="unknown relation"):
        RelationAlgebra(vocabulary={"a"}, table={}, inverses={"a": "b"})
    with pytest.raises(ValueError, match="unknown relation"):
        RelationAlgebra(vocabulary={"a"}, table={}, dimensions={"z": Dimension.CAUSAL})


def test_escalate_and_none_are_valid_table_values():
    alg = RelationAlgebra(
        vocabulary={"a", "b"},
        table={("a", "a"): ESCALATE, ("a", "b"): None},
    )
    assert alg.compose("a", "a") is ESCALATE
    assert alg.compose("a", "b") is None


# ── compose / lookups ─────────────────────────────────────────────

def test_compose_lenient_on_unknown_pair():
    alg = RelationAlgebra(vocabulary={"a", "b"}, table={("a", "b"): "a"})
    assert alg.compose("a", "b") == "a"
    assert alg.compose("b", "a") is None          # absent pair -> no relation
    assert alg.is_relation("a") and not alg.is_relation("zzz")


# ── compose_path: fold semantics ──────────────────────────────────

def test_empty_and_single_chain():
    alg = RelationAlgebra(vocabulary={"a"}, table={})
    assert alg.compose_path([]) == (None, False)
    assert alg.compose_path(["a"]) == ("a", False)


def test_left_fold_transitive_chain():
    # member_of is transitive: (m,m)->m, so m∘m∘m -> m
    alg = RelationAlgebra(vocabulary={"m"}, table={("m", "m"): "m"})
    assert alg.compose_path(["m", "m", "m"]) == ("m", False)


def test_none_breaks_the_chain():
    alg = RelationAlgebra(vocabulary={"a", "b"}, table={("a", "b"): None})
    # a∘b -> None, so the whole path yields None
    assert alg.compose_path(["a", "b", "a"]) == (None, False)


def test_escalate_propagates_and_flags():
    alg = RelationAlgebra(
        vocabulary={"a", "b", "c"},
        table={("a", "b"): ESCALATE, ("b", "c"): "c"},
    )
    result, escalated = alg.compose_path(["a", "b", "c"])
    # once contested, the fold restarts from the next leg (b), b∘c -> c,
    # but the path stays flagged as escalated
    assert escalated is True
    assert result == "c"


def test_escalate_at_final_step_flags():
    alg = RelationAlgebra(vocabulary={"a"}, table={("a", "a"): ESCALATE})
    assert alg.compose_path(["a", "a"]) == (ESCALATE, True)


# ── inverse / dimension ───────────────────────────────────────────

def test_inverse_and_dimension_defaults():
    alg = RelationAlgebra(
        vocabulary={"parent_of", "subsidiary_of", "loose"},
        table={},
        inverses={"parent_of": "subsidiary_of", "subsidiary_of": "parent_of"},
        dimensions={"parent_of": Dimension.STRUCTURAL},
    )
    assert alg.inverse("parent_of") == "subsidiary_of"
    assert alg.inverse("loose") is None
    assert alg.dimension("parent_of") == Dimension.STRUCTURAL
    assert alg.dimension("loose") == Dimension.RELATIONAL   # default floor


# ── behaviour-preservation vs the legal_connection algebra ────────
# A legal-shaped algebra: the mechanism must reproduce the domain laws that used
# to live in host's legal_connection (LC-2 subjection, LC-3/LC-4 escalation,
# transitivity), proving the retirement is behaviour-preserving.

def _legal_algebra() -> RelationAlgebra:
    vocab = {
        "incorporated_in", "established_in", "member_of", "subject_to",
        "bound_by", "party_to", "controls", "parent_of", "subsidiary_of",
    }
    table = {
        # LC-2: establishment + membership climb -> subject_to the higher order
        ("incorporated_in", "member_of"): "subject_to",
        ("established_in", "member_of"): "subject_to",
        ("subject_to", "member_of"): "subject_to",
        ("member_of", "member_of"): "member_of",          # transitive
        ("subject_to", "bound_by"): "bound_by",
        # LC-3: mere party_to a treaty does not reach a private party
        ("incorporated_in", "party_to"): ESCALATE,
        ("subject_to", "party_to"): ESCALATE,
        # LC-4: corporate-group reach is contested
        ("controls", "subject_to"): ESCALATE,
        ("parent_of", "subject_to"): ESCALATE,
        ("controls", "controls"): "controls",             # control is transitive
    }
    inverses = {"parent_of": "subsidiary_of", "subsidiary_of": "parent_of"}
    dims = {"subject_to": Dimension.CAUSAL, "member_of": Dimension.STRUCTURAL}
    return RelationAlgebra(vocabulary=vocab, table=table,
                           inverses=inverses, dimensions=dims)


def test_legal_lc2_incorporation_then_membership_yields_subjection():
    alg = _legal_algebra()
    # a company incorporated in a member state of the EU is subject_to the EU
    assert alg.compose_path(["incorporated_in", "member_of"]) == ("subject_to", False)
    # and subjection climbs the ladder + reaches the instrument the order is bound by
    assert alg.compose_path(
        ["incorporated_in", "member_of", "bound_by"]) == ("bound_by", False)


def test_legal_lc3_treaty_party_escalates():
    alg = _legal_algebra()
    assert alg.compose_path(["incorporated_in", "party_to"]) == (ESCALATE, True)


def test_legal_lc4_corporate_group_reach_escalates():
    alg = _legal_algebra()
    result, escalated = alg.compose_path(["controls", "subject_to"])
    assert result is ESCALATE and escalated is True


def test_legal_transitivity_and_inverse():
    alg = _legal_algebra()
    assert alg.compose_path(["member_of", "member_of", "member_of"]) == ("member_of", False)
    assert alg.inverse("parent_of") == "subsidiary_of"
    assert alg.dimension("subject_to") == Dimension.CAUSAL
