# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Deprecation shims kept for one release after the Federation -> 5D/corpus
rename: the old names still work, warn, and return equal results.
"""
from __future__ import annotations

import importlib
import warnings

import pytest

from loomground_solver import fingerprint, narrow
from loomground_solver.addons.metacognition import ImprovementKind


def _prob(forces, node="x"):
    edges = [{"subject": "s", "predicate": "p", "object": node,
              "dimension": d, "polarity": s} for d, s in forces]
    return fingerprint(pairs=[{"id": "i", "edges": edges}], filters=["contradiction"])


# ── loomground_solver.federation — deprecated shim module ────────────────────

def test_federation_module_import_warns():
    import loomground_solver.federation as fed_first_import  # noqa: F401
    # Force a fresh import warning regardless of module-cache state elsewhere
    # in the test session by reloading the already-imported shim.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import loomground_solver.federation as fed
        importlib.reload(fed)
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_federation_module_reexports_same_objects_as_corpus():
    import loomground_solver.corpus as corpus
    import loomground_solver.federation as fed

    assert fed.structural_transform is corpus.structural_transform
    assert fed.derive_solution is corpus.derive_solution
    assert fed.UNDETERMINED is corpus.UNDETERMINED


def test_federation_module_yields_equal_results_to_corpus():
    import loomground_solver.corpus as corpus
    import loomground_solver.federation as fed

    physics = [
        (_prob([("structural", +1), ("causal", -1)], "beam"), _prob([("structural", +1)], "beam")),
    ]
    problem = _prob([("intentional", +1), ("relational", -1)], "record")
    assert fed.derive_solution(problem, physics) == corpus.derive_solution(problem, physics)


# ── narrow(problem_fp, corpus=None, *, federation=<deprecated>) ─────────────

def test_narrow_corpus_keyword_and_positional_are_equivalent():
    physics = [
        (_prob([("structural", +1), ("causal", -1)], "beam"), _prob([("structural", +1)], "beam")),
    ]
    problem = _prob([("intentional", +1), ("relational", -1)], "record")
    assert narrow(problem, physics) == narrow(problem, corpus=physics)


def test_narrow_federation_keyword_warns_and_matches_corpus_keyword():
    physics = [
        (_prob([("structural", +1), ("causal", -1)], "beam"), _prob([("structural", +1)], "beam")),
    ]
    problem = _prob([("intentional", +1), ("relational", -1)], "record")

    with pytest.warns(DeprecationWarning):
        out_old = narrow(problem, federation=physics)
    out_new = narrow(problem, corpus=physics)
    assert out_old == out_new


def test_narrow_both_corpus_and_federation_raises_type_error():
    physics = [
        (_prob([("structural", +1), ("causal", -1)], "beam"), _prob([("structural", +1)], "beam")),
    ]
    problem = _prob([("intentional", +1), ("relational", -1)], "record")
    with pytest.raises(TypeError):
        narrow(problem, corpus=physics, federation=physics)


# ── ImprovementKind.FEDERATION_EXAMPLE / 'federation_example' alias ─────────

def test_improvement_kind_old_value_resolves_to_corpus_example_with_warning():
    with pytest.warns(DeprecationWarning):
        resolved = ImprovementKind("federation_example")
    assert resolved is ImprovementKind.CORPUS_EXAMPLE
    assert resolved == "corpus_example"


def test_improvement_kind_old_attribute_resolves_to_corpus_example_with_warning():
    with pytest.warns(DeprecationWarning):
        resolved = ImprovementKind.FEDERATION_EXAMPLE
    assert resolved is ImprovementKind.CORPUS_EXAMPLE
    assert resolved == "corpus_example"


def test_improvement_kind_corpus_example_is_the_current_value():
    assert ImprovementKind.CORPUS_EXAMPLE == "corpus_example"
