# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Definitional closure: transitively expand a defined term through INJECTED
definitional edges, detect definitional cycles (report, do not hang), and yield
the closed definition for substitution into subsumption.

The four load-bearing branches: a chain expands fully; a diamond closes without
duplication; a cycle is *reported* (open + ring), never looped on; an undefined
term is an explicit unknown, never a fabricated definition. Plus: relation-type
coherence demotes a contested branch to OPEN, and the expansion substitutes into
:mod:`subsumption`.
"""
from __future__ import annotations

from loomground_solver.definition_closure import (
    ClosedDefinition, close_definition,
)
from loomground_solver.dimensions import Dimension
from loomground_solver.reasoning import Edge
from loomground_solver.relation import ESCALATE, RelationAlgebra
from loomground_solver.subsumption import Rule, holds, subsume


def E(subject: str, predicate: str, obj: str) -> Edge:
    """A definitional edge (STRUCTURAL: is-a / defined-as / has-element)."""
    return Edge(subject, predicate, obj, Dimension.STRUCTURAL)


# ── 1. chain: A → B → C expands fully ─────────────────────────────────────────

def test_chain_expands_fully():
    edges = [E("A", "defined_as", "B"), E("B", "defined_as", "C")]
    r = close_definition("A", edges)
    assert r.defined
    assert not r.open
    assert r.cycle is None
    # transitive closure = direct token B *and* the token B expands to, C
    assert r.tokens == frozenset({"B", "C"})


def test_chain_expansion_is_transitive_not_just_one_hop():
    edges = [E("A", "is_a", "B"), E("B", "is_a", "C"), E("C", "is_a", "D")]
    r = close_definition("A", edges)
    assert r.tokens == frozenset({"B", "C", "D"})


# ── 2. diamond: (A→B, A→C, B→D, C→D) closes without duplication ────────────────

def test_diamond_closes_without_duplication():
    edges = [
        E("A", "is_a", "B"), E("A", "is_a", "C"),
        E("B", "has_element", "D"), E("C", "has_element", "D"),
    ]
    r = close_definition("A", edges)
    assert not r.open
    # D is reached along two distinct paths but appears once in the closure
    assert r.tokens == frozenset({"B", "C", "D"})
    # …and the provenance keeps *both* derivations of D (dedup is on the token
    # set, not a lost path)
    d_paths = [p for p in r.paths if p["object"] == "D"]
    assert len(d_paths) == 2


# ── 3. cycle: A → B → A is reported, never looped on ──────────────────────────

def test_cycle_reported_not_infinite_loop():
    edges = [E("A", "is_a", "B"), E("B", "is_a", "A")]
    r = close_definition("A", edges)      # must return, not hang
    assert r.open                          # escalates, first-class
    assert r.cycle is not None
    assert "A" in r.cycle and "B" in r.cycle
    assert r.cycle[0] == r.cycle[-1]       # the ring is closed


def test_self_definition_is_a_cycle():
    # T defined in terms of itself — the direct self-loop the acyclic closures
    # would silently skip (seeded visited=(T,)).
    edges = [E("T", "defined_as", "T")]
    r = close_definition("T", edges)
    assert r.open
    assert r.cycle == ("T", "T")


def test_cycle_deeper_than_the_start_term():
    # The loop is B↔C; A merely reaches it. Detection is over the reachable
    # subgraph, not only self-loops on the start term.
    edges = [E("A", "is_a", "B"), E("B", "is_a", "C"), E("C", "is_a", "B")]
    r = close_definition("A", edges)
    assert r.open
    assert r.cycle is not None
    assert "B" in r.cycle and "C" in r.cycle


# ── 4. undefined term: explicit empty/unknown, never fabricated ───────────────

def test_undefined_term_is_explicit_unknown():
    edges = [E("A", "is_a", "B")]
    r = close_definition("Z", edges)       # Z is named by no edge
    assert r.defined is False
    assert r.tokens == frozenset()
    assert r.open is False                  # unknown ≠ contested
    assert r.cycle is None
    assert "undefined" in r.reason


def test_empty_edge_set_yields_unknown():
    r = close_definition("anything", [])
    assert r.defined is False
    assert r.tokens == frozenset()


# ── 5. relation-type coherence: a contested chain is demoted to OPEN ──────────

def test_contested_composition_demoted_to_open():
    # licenses∘sublicenses is CONTESTED (ESCALATE) in the injected algebra, so the
    # 2-hop branch to C is withheld; the 1-hop token B still settles.
    edges = [E("A", "licenses", "B"), E("B", "sublicenses", "C")]
    algebra = RelationAlgebra(
        vocabulary={"licenses", "sublicenses"},
        table={("licenses", "sublicenses"): ESCALATE},
    )
    r = close_definition("A", edges, relations=algebra)
    assert r.open
    assert "B" in r.tokens                  # 1-hop settled
    assert "C" not in r.tokens              # 2-hop demoted, not admitted
    assert any(c["object"] == "C" for c in r.contested)


def test_coherent_relation_chain_is_admitted():
    # owns∘owns → owns is settled in the algebra, so the full chain admits.
    edges = [E("A", "owns", "B"), E("B", "owns", "C")]
    algebra = RelationAlgebra(
        vocabulary={"owns"},
        table={("owns", "owns"): "owns"},
    )
    r = close_definition("A", edges, relations=algebra)
    assert not r.open
    assert r.tokens == frozenset({"B", "C"})


def test_no_algebra_means_coherence_not_asserted():
    # Without an algebra the reach is admitted as-is (coherence is opt-in).
    edges = [E("A", "licenses", "B"), E("B", "sublicenses", "C")]
    r = close_definition("A", edges)
    assert not r.open
    assert r.tokens == frozenset({"B", "C"})


# ── 6. substitution seam into subsumption ─────────────────────────────────────

def test_expansion_substitutes_into_subsumption_as_facts():
    edges = [E("personal_data", "is_a", "identifier"),
             E("identifier", "is_a", "attribute")]
    r = close_definition("personal_data", edges)
    facts = set(r.as_facts()) | {"personal_data"}
    # a rule whose condition names a *transitively* defining token now fires
    rule = Rule(id="r", conditions=("attribute",), consequence="regulated")
    assert subsume(rule, facts).applicable
    assert holds("identifier", facts)


def test_expansion_substitutes_via_judge_seam():
    edges = [E("controller", "is_a", "processor"),
             E("processor", "is_a", "actor")]
    r = close_definition("controller", edges)
    judge = r.judge()
    # the open literal is decided by membership in the expansion
    assert holds("actor", set(), judge=judge)
    assert not holds("stranger", set(), judge=judge)


# ── 7. result surface ─────────────────────────────────────────────────────────

def test_to_dict_is_serialisable_and_named():
    edges = [E("A", "is_a", "B"), E("B", "is_a", "A")]
    d = close_definition("A", edges).to_dict()
    assert d["term"] == "A"
    assert d["open"] is True
    assert d["cycle"][0] == d["cycle"][-1]
    assert isinstance(d["tokens"], list)


def test_result_is_a_frozen_dataclass():
    r = close_definition("A", [E("A", "is_a", "B")])
    assert isinstance(r, ClosedDefinition)
    import dataclasses
    assert dataclasses.is_dataclass(r)
