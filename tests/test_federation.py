# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Reasoning in fingerprint space: derive an unknown problem's solution structure
by INFERENCE over the federation's problem→solution transform — not by lookup."""
from __future__ import annotations

import pytest

from loomground_solver import fingerprint, structural_transform, derive_solution


def _fp(n_causal, n_temporal=0):
    edges = ([{"subject": f"c{i}", "predicate": "p", "object": f"o{i}", "dimension": "causal"}
              for i in range(n_causal)]
             + [{"subject": f"t{i}", "predicate": "p", "object": f"u{i}", "dimension": "temporal"}
                for i in range(n_temporal)])
    return fingerprint(pairs=[{"id": "x", "edges": edges}], filters=["logical_form"])


def test_transform_learned_where_the_federation_agrees():
    # every pair's solution adds exactly one causal edge over its problem
    pairs = [(_fp(1), _fp(2)), (_fp(3), _fp(4)), (_fp(0), _fp(1))]
    t = structural_transform(pairs)
    assert t["logical_form/dimensions/causal"] == 1.0        # a determined delta
    assert t["logical_form/dimensions/temporal"] == 0.0       # unchanged, determined


def test_derive_narrows_the_solution_by_inference_not_lookup():
    pairs = [(_fp(1), _fp(2)), (_fp(3), _fp(4))]              # +1 causal, consistent
    out = derive_solution(_fp(5), pairs)                     # a problem never seen
    assert out["determined"]["logical_form/dimensions/causal"] == 6.0   # 5 + 1, derived
    assert out["undetermined"] == [] and out["determinacy"] == 1.0


def test_disagreement_is_undetermined_and_escalates_not_guessed():
    # one pair adds a causal edge, another removes one -> the delta is not pinned
    pairs = [(_fp(1), _fp(2)), (_fp(3), _fp(2))]
    t = structural_transform(pairs)
    assert t["logical_form/dimensions/causal"] is None       # UNDETERMINED
    out = derive_solution(_fp(4), pairs)
    assert "logical_form/dimensions/causal" in out["undetermined"]
    assert out["determinacy"] < 1.0                          # honestly not fully pinned


def test_empty_federation_determines_nothing():
    out = derive_solution(_fp(2), [])
    assert out["determined"] == {} and out["determinacy"] == 0.0


def test_version_mismatch_is_incomparable():
    a, b = _fp(1), _fp(2)
    b2 = dict(b); b2["version"] = "fp-99"
    with pytest.raises(ValueError):
        structural_transform([(a, b2)])


def test_mismatched_facet_shapes_are_incomparable_not_silently_zeroed():
    # a problem built with one lens, its "solution" with another -> the missing
    # facet must NOT be read as zero and reported as a determined delta
    logical = fingerprint(pairs=[{"id": "x", "edges": []}], filters=["logical_form"])
    stats = fingerprint(pairs=[{"id": "x", "edges": []}], filters=["statistics"])
    with pytest.raises(ValueError):
        structural_transform([(logical, stats)])


# ── negative space: reasoning over the set-valued coordinates ────────────────
# (the sharp discriminator — what a solution CLOSES, not just what it adds)

def _ns(gaps):
    """A fingerprint whose negative space is a set of reported gaps."""
    return fingerprint(case={"gaps": list(gaps), "chain": [], "grounds": []},
                       filters=["negative_space"])


def test_negative_space_count_transfers_but_identity_escalates():
    # every solution closes exactly ONE gap, but a DIFFERENT one each time
    pairs = [(_ns(["g1", "g2", "g3"]), _ns(["g1", "g2"])),
             (_ns(["a", "b", "c"]),    _ns(["a", "b"]))]
    t = structural_transform(pairs)
    # the structural count is agreed and transfers across domains …
    assert t["negative_space/gaps#n"] == -1.0
    # … but WHICH gap is domain-bound, so the identity is not pinned — it escalates
    assert t["negative_space/gaps"] is None
    out = derive_solution(_ns(["x", "y", "z", "w"]), pairs)   # a problem never seen
    assert out["determined"]["negative_space/gaps#n"] == 3.0  # 4 - 1, derived count
    assert "negative_space/gaps" in out["undetermined"]       # identity escalates
    assert out["determinacy"] < 1.0                           # honestly not fully pinned


def test_systematic_defeater_is_derived_when_the_federation_agrees():
    # the SAME gap G0 is closed in every pair -> the federation pins its identity
    pairs = [(_ns(["G0", "x"]), _ns(["x"])),
             (_ns(["G0", "y"]), _ns(["y"]))]
    t = structural_transform(pairs)
    assert t["negative_space/gaps"] == {"add": frozenset(), "remove": frozenset({"G0"})}
    out = derive_solution(_ns(["G0", "z"]), pairs)            # unseen problem carrying G0
    assert out["determined_sets"]["negative_space/gaps"] == ["z"]   # G0 systematically closed
    assert out["undetermined"] == []                          # fully pinned here
