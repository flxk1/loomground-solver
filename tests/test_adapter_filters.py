# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The worked-example adapter filters: a statistics-methods lens and a Walton
argumentation-scheme lens. Importing them registers them into the global filter
set; they then compose with fingerprint()/distance() like any core filter."""
from __future__ import annotations

from loomground_solver import (
    FILTERS,
    distance,
    fingerprint,
    install_reference_filters,
)
from loomground_solver.adapters.filters import (
    argumentation_schemes,
    statistics_methods,
)

install_reference_filters()


def _edge(s, o, dim="causal", weight=1.0):
    return {"id": f"{s}-{o}", "edges": [
        {"subject": s, "predicate": "p", "object": o, "dimension": dim, "weight": weight}]}


def test_both_adapter_filters_are_registered():
    assert "statistics_methods" in FILTERS
    assert "argumentation_schemes" in FILTERS


def test_statistics_methods_moments_correlation_and_test_statistic():
    pairs = [_edge("A", "B", "causal", 1.0), _edge("C", "D", "causal", 0.5),
             _edge("E", "F", "temporal", 0.5)]
    fp = fingerprint(pairs=pairs, filters=["statistics_methods"])
    s = fp["facets"]["statistics_methods"]
    assert s["n"] == 3
    assert s["mean"] == round((1.0 + 0.5 + 0.5) / 3, 6)
    assert s["stdev"] > 0.0                        # weights vary
    assert -1.0 <= s["weight_position_correlation"] <= 1.0
    # two dims used unevenly (causal×2, temporal×1) -> chi2 > 0 vs uniform, dof=1
    assert s["dimension_chi2_vs_uniform"] > 0.0 and s["dimension_dof"] == 1
    assert 0.0 <= s["dimension_gini"] <= 1.0


def test_statistics_uniform_weights_have_zero_spread():
    pairs = [_edge("A", "B", "causal", 1.0), _edge("C", "D", "causal", 1.0)]
    s = fingerprint(pairs=pairs, filters=["statistics_methods"])["facets"]["statistics_methods"]
    assert s["variance"] == 0.0 and s["stdev"] == 0.0 and s["skewness"] == 0.0


def test_walton_schemes_and_critical_question_budget():
    # causal edge -> cause-to-effect (3 CQs); lex-superior fired -> authority (6 CQs)
    fp = fingerprint(pairs=[_edge("A", "B", "causal")], fired_rules=["lex-superior"],
                     filters=["argumentation_schemes"])
    a = fp["facets"]["argumentation_schemes"]
    assert a["cause-to-effect"] == 1 and a["expert-opinion-authority"] == 1
    assert a["critical_questions_open"] == 3 + 6      # defeasibility budget

    # analogy edge alone -> 3 CQs
    b = fingerprint(pairs=[_edge("A", "B", "relational")],
                    filters=["argumentation_schemes"])["facets"]["argumentation_schemes"]
    assert b["analogy"] == 1 and b["critical_questions_open"] == 3


def test_adapter_filters_participate_in_distance():
    a = fingerprint(pairs=[_edge("A", "B", "causal", 1.0)],
                    filters=["statistics_methods", "argumentation_schemes"])
    b = fingerprint(pairs=[_edge("A", "B", "relational", 0.2)],
                    filters=["statistics_methods", "argumentation_schemes"])
    d = distance(a, b)
    assert 0.0 < d <= 1.0                             # different scheme + weight -> farther
    assert distance(a, a) == 0.0


def test_default_fingerprint_now_includes_adapter_filters():
    # once imported, a default (all-filters) fingerprint carries them too
    fp = fingerprint(pairs=[_edge("A", "B", "causal")])
    assert "statistics_methods" in fp["facets"]
    assert "argumentation_schemes" in fp["facets"]
