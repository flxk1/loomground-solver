# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Dedup — canonical identity + order-stable, provenance-preserving merge.

Identical rules/norms collapse to one representative while every source id is
kept; condition order and exceptions do not affect identity; differing records
stay apart; the pass is deterministic. Imports the module directly (public
exports are wired separately by the supervisor)."""
from __future__ import annotations

import pytest

from loomground_solver.subsumption import Rule
from loomground_solver.scenario import Norm
from loomground_solver.dedup import (
    CanonicalKey,
    MergeGroup,
    DedupResult,
    canonical_key,
    dedup,
)


def test_identical_rules_collapse_to_one_recording_both_sources():
    # Same Tatbestand→Rechtsfolge/act/modality, different id + source.
    a = Rule("r1", conditions=("p", "q"), consequence="c", act="erase",
             modality="obligatory", source="src-a")
    b = Rule("r2", conditions=("p", "q"), consequence="c", act="erase",
             modality="obligatory", source="src-b")
    result = dedup([a, b])
    assert isinstance(result, DedupResult)
    assert len(result.records) == 1
    assert result.records[0] is a                     # representative = first member
    key = canonical_key(a)
    assert result.merge_map[key] == ("src-a", "src-b")  # both sources, in order
    assert len(result.groups) == 1
    group = result.groups[0]
    assert isinstance(group, MergeGroup)
    assert group.members == (a, b)


def test_differing_rules_are_kept_separate():
    a = Rule("r1", conditions=("p", "q"), consequence="c", act="erase",
             modality="obligatory", source="src-a")
    b = Rule("r2", conditions=("p", "different"), consequence="c", act="erase",
             modality="obligatory", source="src-b")
    result = dedup([a, b])
    assert len(result.groups) == 2
    assert len(result.records) == 2
    assert canonical_key(a) != canonical_key(b)
    assert len(result.merge_map) == 2


def test_condition_order_is_irrelevant_frozenset_key():
    a = Rule("r1", conditions=("a", "b"), consequence="c", act="x",
             modality="permitted", source="s1")
    b = Rule("r2", conditions=("b", "a"), consequence="c", act="x",
             modality="permitted", source="s2")
    assert canonical_key(a) == canonical_key(b)        # frozenset canonicalisation
    result = dedup([a, b])
    assert len(result.groups) == 1
    assert result.merge_map[canonical_key(a)] == ("s1", "s2")


def test_exceptions_are_not_part_of_identity():
    # Exceptions differ, everything else identical -> still one group.
    a = Rule("r1", conditions=("p",), consequence="c", exceptions=("legal-hold",),
             act="erase", modality="obligatory", source="src-a")
    b = Rule("r2", conditions=("p",), consequence="c", exceptions=("consent", "minor"),
             act="erase", modality="obligatory", source="src-b")
    assert canonical_key(a) == canonical_key(b)
    result = dedup([a, b])
    assert len(result.groups) == 1
    assert result.merge_map[canonical_key(a)] == ("src-a", "src-b")


def test_norms_dedup_by_act_and_deontic():
    n1 = Norm("erase", "obligatory", source="auth-1")
    n2 = Norm("erase", "obligatory", source="auth-2")
    n3 = Norm("erase", "permitted", source="auth-3")     # different deontic
    result = dedup([n1, n2, n3])
    assert len(result.groups) == 2
    assert result.merge_map[canonical_key(n1)] == ("auth-1", "auth-2")
    assert result.merge_map[canonical_key(n3)] == ("auth-3",)
    # Norm canonical key: empty conditions, empty consequence.
    key = canonical_key(n1)
    assert key.conditions == frozenset()
    assert key.consequence == ""
    assert key.act == "erase" and key.modality == "obligatory"


def test_order_stability_and_determinism():
    a = Rule("r1", conditions=("p",), consequence="c", act="x",
             modality="obligatory", source="s-a")
    b = Rule("r2", conditions=("q",), consequence="d", act="y",
             modality="permitted", source="s-b")
    a2 = Rule("r3", conditions=("p",), consequence="c", act="x",
              modality="obligatory", source="s-a2")
    records = [a, b, a2]
    first = dedup(records)
    second = dedup(records)
    # representative = first occurrence; first-appearance order preserved.
    assert first.records == [a, b]
    assert first.records[0] is a and first.records[1] is b
    # two runs agree exactly.
    assert first.merge_map == second.merge_map
    assert [r for r in first.records] == [r for r in second.records]
    assert first.merge_map[canonical_key(a)] == ("s-a", "s-a2")


# --- edge cases ------------------------------------------------------------

def test_canonical_key_rejects_unknown_record():
    with pytest.raises(TypeError):
        canonical_key(object())
    with pytest.raises(TypeError):
        canonical_key("not-a-record")


def test_empty_input_yields_empty_result():
    result = dedup([])
    assert result.records == []
    assert result.groups == []
    assert result.merge_map == {}


def test_default_source_of_falls_back_to_id_then_str():
    # Rule with no source -> uses its id.
    r = Rule("only-id", conditions=("p",), consequence="c", act="x",
             modality="obligatory")  # source defaults to ""
    result = dedup([r])
    assert result.merge_map[canonical_key(r)] == ("only-id",)


def test_custom_source_of_is_honoured():
    a = Rule("r1", conditions=("p",), consequence="c", act="x",
             modality="obligatory", source="ignored-a")
    b = Rule("r2", conditions=("p",), consequence="c", act="x",
             modality="obligatory", source="ignored-b")
    result = dedup([a, b], source_of=lambda rec: rec.id)
    assert result.merge_map[canonical_key(a)] == ("r1", "r2")


def test_canonical_key_is_hashable_and_frozen():
    k = canonical_key(Norm("erase", "obligatory", source="s"))
    # usable as a dict key (already relied on by merge_map) and immutable.
    assert {k: 1}[k] == 1
    with pytest.raises(Exception):
        k.act = "changed"  # frozen dataclass
