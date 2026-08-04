# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Exhaustive stress over the 5D composition algebra.

``dimensions.py`` and ``reasoning.py`` both rest on two claims about the
composition table that were, until now, only asserted in prose:

* the table is **total** — every ordered pair of the five dimensions has a
  defined composite, so ``compose`` never raises on a well-formed edge chain;
* the algebra is **not fully associative** — exactly two of the 125 ordered
  triples compose to a different dimension depending on grouping, which is
  *why* :func:`compose_paths` fixes a canonical **left-fold** order rather than
  treating grouping as free.

The 5×5 (25 pairs) and 5×5×5 (125 triples) spaces are small enough to test
**exhaustively**, so this file enumerates them in full rather than sampling.
If a table entry ever changes, the exact-divergence assertion below fails and
names the triple that moved — the canonical order can never drift unnoticed.
"""
from __future__ import annotations

import itertools

from loomground_solver.dimensions import (
    COMPOSITION_TABLE,
    Dimension,
    compose,
    compose_weights,
)
from loomground_solver.reasoning import compose_paths, extract_edges

DIMS = list(Dimension)

# The two triples whose composite depends on grouping. Both are
# ``causal ∘ {intentional|temporal} ∘ structural``: left-folding (start→end)
# lands on STRUCTURAL, right-folding on CAUSAL. Left-fold is canonical, so the
# walk always yields STRUCTURAL for these — see ``compose_paths``.
NON_ASSOCIATIVE = {
    (Dimension.CAUSAL, Dimension.INTENTIONAL, Dimension.STRUCTURAL),
    (Dimension.CAUSAL, Dimension.TEMPORAL, Dimension.STRUCTURAL),
}


def test_two_step_table_is_total():
    """Every ordered pair of dimensions has a defined composite."""
    for a, b in itertools.product(DIMS, DIMS):
        assert (a, b) in COMPOSITION_TABLE, f"missing composite for ({a}, {b})"
        assert isinstance(compose(a, b), Dimension)
    assert len(COMPOSITION_TABLE) == 25


def test_diagonal_is_idempotent():
    """A chain that stays in one dimension composes to that dimension."""
    for d in DIMS:
        assert compose(d, d) == d


def test_associativity_diverges_on_exactly_the_two_known_triples():
    """Exhaustively over all 125 triples, left- vs right-grouping disagree on
    precisely the two documented triples — no more, no fewer."""
    diverging = {
        (a, b, c)
        for a, b, c in itertools.product(DIMS, DIMS, DIMS)
        if compose(compose(a, b), c) != compose(a, compose(b, c))
    }
    assert diverging == NON_ASSOCIATIVE, (
        "associativity profile drifted; the composition table changed. "
        f"now-diverging: {sorted(map(str, diverging))}"
    )


def test_left_fold_result_is_pinned_for_the_non_associative_triples():
    """For each contested triple, left-grouping is STRUCTURAL, right is CAUSAL —
    documenting the concrete values the canonical order commits to."""
    for a, b, c in NON_ASSOCIATIVE:
        assert compose(compose(a, b), c) == Dimension.STRUCTURAL
        assert compose(a, compose(b, c)) == Dimension.CAUSAL


def _chain(a, b, c):
    """Three unit-weight edges A→B→C→D carrying dimensions a, b, c."""
    return extract_edges([{
        "id": "t", "solution": {"confidence": 1.0},
        "edges": [
            {"subject": "A", "predicate": "p", "object": "B", "dimension": a.value},
            {"subject": "B", "predicate": "p", "object": "C", "dimension": b.value},
            {"subject": "C", "predicate": "p", "object": "D", "dimension": c.value},
        ],
    }])


def test_compose_paths_takes_the_left_fold_on_contested_triples():
    """The walk must realise the *left*-fold — the whole reason a fixed order is
    required. On both non-associative triples the A→D inference is STRUCTURAL."""
    for a, b, c in NON_ASSOCIATIVE:
        inf = compose_paths(_chain(a, b, c), start="A", max_depth=3)
        a_to_d = [i for i in inf if i.subject == "A" and i.object == "D"]
        assert a_to_d, f"no 3-hop inference for {(a, b, c)}"
        assert a_to_d[0].dimension == Dimension.STRUCTURAL
        assert a_to_d[0].dimension_chain == [a.value, b.value, c.value]


def test_confidence_composition_is_monotone_and_bounded():
    """Confidence is multiplicative in [0, 1]: composing never raises it, and a
    chain of sub-unit weights is non-increasing — the property subtree pruning
    and branch-and-bound both rely on."""
    weights = [0.0, 0.1, 0.5, 0.9, 1.0]
    for w1, w2 in itertools.product(weights, weights):
        c = compose_weights(w1, w2)
        assert 0.0 <= c <= 1.0
        assert c <= w1 and c <= w2


def test_left_fold_over_a_long_chain_matches_manual_reduction():
    """A 5-hop path's composed dimension equals the explicit left reduction over
    the same dimension sequence — the walk's incremental fold is faithful."""
    seq = [Dimension.CAUSAL, Dimension.TEMPORAL, Dimension.STRUCTURAL,
           Dimension.INTENTIONAL, Dimension.RELATIONAL]
    edges = extract_edges([{
        "id": "t", "solution": {"confidence": 1.0},
        "edges": [
            {"subject": f"N{i}", "predicate": "p", "object": f"N{i + 1}",
             "dimension": d.value}
            for i, d in enumerate(seq)
        ],
    }])
    manual = seq[0]
    for d in seq[1:]:
        manual = compose(manual, d)
    inf = compose_paths(edges, start="N0", max_depth=len(seq))
    longest = max(inf, key=lambda i: i.hops)
    assert longest.hops == len(seq)
    assert longest.dimension == manual
