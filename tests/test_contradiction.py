# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""#2 — fingerprint the CONTRADICTION, not the surface. The contradiction filter
abstracts a problem's edges to a domain-neutral invariant (opposing forces on a
shared node), so a legal problem can be solved by the structural shape of a physics
solution. Cross-domain transfer is proven at the federation layer: the invariant is
derived; the domain-specific detail escalates."""
from __future__ import annotations

from loomground_solver import fingerprint, derive_solution, structural_transform


def _prob(forces, node="x"):
    """A one-problem fingerprint from ``forces`` = [(dimension, polarity_sign), …]
    all acting on the same contended ``node``."""
    edges = [{"subject": "s", "predicate": "p", "object": node,
              "dimension": d, "polarity": s} for d, s in forces]
    return fingerprint(pairs=[{"id": "i", "edges": edges}], filters=["contradiction"])


# ── the filter extracts opposition, domain-neutrally ─────────────────────────

def test_opposing_forces_on_a_shared_node_are_a_contradiction():
    fp = _prob([("structural", +1), ("causal", -1)], node="beam")["facets"]["contradiction"]
    assert fp["contradiction_count"] == 1
    assert fp["tradeoff"] == 1                    # the two forces span two dimensions
    assert fp["same_dimension_tension"] == 0


def test_no_opposition_is_no_contradiction():
    fp = _prob([("structural", +1), ("causal", +1)], node="beam")["facets"]["contradiction"]
    assert fp["contradiction_count"] == 0


def test_the_invariant_is_shared_across_domains_but_the_dimensions_are_not():
    physics = _prob([("structural", +1), ("causal", -1)], node="beam")["facets"]["contradiction"]
    legal = _prob([("intentional", +1), ("relational", -1)], node="data")["facets"]["contradiction"]
    # same invariant shape — a single cross-dimension trade-off …
    assert physics["contradiction_count"] == legal["contradiction_count"] == 1
    assert physics["tradeoff"] == legal["tradeoff"] == 1
    # … but the AXES carrying it differ (domain-bound: escalates across domains)
    assert physics["tradeoff_axes"] == ["causal|structural"]
    assert legal["tradeoff_axes"] == ["intentional|relational"]
    assert physics["tradeoff_axes"] != legal["tradeoff_axes"]


# ── the on-vision proof: derive a LEGAL solution's structure from PHYSICS ─────

def test_legal_solution_invariant_is_derived_from_a_physics_federation():
    # a federation of PHYSICS problem->solution pairs: each resolves its trade-off
    physics_pairs = [
        (_prob([("structural", +1), ("causal", -1)], "beam"), _prob([("structural", +1)], "beam")),
        (_prob([("temporal", +1), ("causal", -1)], "signal"), _prob([("temporal", +1)], "signal")),
    ]
    t = structural_transform(physics_pairs)
    assert t["contradiction/contradiction_count"] == -1.0     # solutions resolve the contradiction
    assert t["contradiction/tradeoff"] == -1.0

    # a LEGAL problem the federation has never seen (disclosure vs privacy)
    legal_problem = _prob([("intentional", +1), ("relational", -1)], "personal-record")
    out = derive_solution(legal_problem, physics_pairs)
    # the invariant transfers: the derived legal solution RESOLVES its contradiction,
    # a structure composed from physics regularity — not fetched from a neighbour
    assert out["determined"]["contradiction/contradiction_count"] == 0.0
    assert out["determined"]["contradiction/tradeoff"] == 0.0


def test_disagreement_across_domains_escalates_not_guesses():
    # one pair resolves the contradiction, another leaves it standing -> not pinned
    pairs = [
        (_prob([("structural", +1), ("causal", -1)], "beam"), _prob([("structural", +1)], "beam")),
        (_prob([("structural", +1), ("causal", -1)], "beam"), _prob([("structural", +1), ("causal", -1)], "beam")),
    ]
    t = structural_transform(pairs)
    assert t["contradiction/contradiction_count"] is None     # UNDETERMINED
    out = derive_solution(_prob([("intentional", +1), ("relational", -1)], "data"), pairs)
    assert "contradiction/contradiction_count" in out["undetermined"]
