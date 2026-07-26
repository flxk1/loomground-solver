"""The two-stage claim-axes adapter: bounds-checked decoding, no invented semantics.

Stage 1 (``ClaimAxesDecoder``) preserves recognized axes and rejects anything
out of bounds, fail-closed. Stage 2 (``ClaimAxesProfile``) is the versioned
per-axis decision record; every decision is inert and rides along as
metadata. This is load-bearing: a negative polarity must never mint
an attack relation.
"""
import pytest

from loomground_solver.adapters.versum import (
    CLAIM_AXES_SCHEMA, ClaimAxesDecoder, ClaimAxesProfile,
)
from loomground_solver.interop import Candidate


def candidate(axes=None, evidence_extra=None):
    structural = {"schema": CLAIM_AXES_SCHEMA}
    if axes is not None:
        structural["axes"] = axes
    if evidence_extra:
        structural.update(evidence_extra)
    return Candidate(candidate_id="claim-1",
                     claim="Controllers must notify the authority.",
                     structural_evidence=structural)


def test_recognized_axes_are_preserved_verbatim_with_the_profile():
    axes = {"predicate": "requires", "modality": "obligation",
            "polarity": "negative", "quantification": "universal",
            "domain": "data-protection"}
    out = ClaimAxesDecoder().compile(candidate(axes))
    facets = out["pairs"][0]["problem"]["facets"]
    assert facets["claim_axes"] == axes
    assert facets["semantic_profile"]["profile_id"] == \
        "loomground.versum.claim-axes.inert"
    assert facets["semantic_profile"]["axes"]["polarity"] == "annotation"
    assert out["schema"] == CLAIM_AXES_SCHEMA


def test_negative_polarity_never_invents_an_attack_or_edge():
    out = ClaimAxesDecoder().compile(candidate({"polarity": "negative"}))
    assert out["attacks"] == []
    assert out["pairs"][0]["edges"] == []


def test_axes_object_is_required_but_may_be_a_subset_or_empty():
    # A conforming producer always emits the key; absence is malformed or
    # version-skewed output and must be rejected.
    with pytest.raises(ValueError, match="must carry an axes object"):
        ClaimAxesDecoder().compile(candidate(None))
    assert ClaimAxesDecoder().compile(candidate({}))["pairs"]
    out = ClaimAxesDecoder().compile(candidate({"domain": "gdpr"}))
    assert out["pairs"][0]["problem"]["facets"]["claim_axes"] == {"domain": "gdpr"}


@pytest.mark.parametrize("bad, message", [
    (candidate({"flavor": "spicy"}), "unknown claim axes"),
    (candidate({"predicate": ""}), "non-empty string"),
    (candidate({"predicate": 7}), "non-empty string"),
    (candidate({"predicate": "x" * 257}), "exceeds 256"),
    (candidate("not-a-dict"), "must be an object"),
    (candidate({}, evidence_extra={"attacks": [["a", "b"]]}), "unknown keys"),
])
def test_out_of_bounds_evidence_is_rejected_fail_closed(bad, message):
    with pytest.raises(ValueError, match=message):
        ClaimAxesDecoder().compile(bad)


def test_decoder_only_advertises_the_claim_axes_schema():
    decoder = ClaimAxesDecoder()
    assert decoder.supports(CLAIM_AXES_SCHEMA)
    assert not decoder.supports("")
    assert not decoder.supports("reasoning.edges/v1")


def test_profile_is_versioned_and_every_axis_decision_is_explicit():
    profile = ClaimAxesProfile().to_dict()
    assert profile["version"]
    assert set(profile["axes"]) == {"predicate", "modality", "polarity",
                                    "quantification", "domain"}
    # The base profile ships no semantics: every decision is the inert one, and
    # polarity's only alternative is negation/annotation — an attack mapping must
    # never appear in any profile version.
    assert profile["axes"]["predicate"] == "descriptive"
    assert "attack" not in profile["axes"]["polarity"]


def test_profile_decisions_are_validated_against_closed_sets():
    # A typo like polarity="attack" must be an error at construction, never
    # a serialized declaration.
    with pytest.raises(ValueError, match="polarity"):
        ClaimAxesProfile(polarity="attack")
    with pytest.raises(ValueError, match="modality"):
        ClaimAxesProfile(modality="deontic")  # not in the closed modality set
    with pytest.raises(ValueError, match="required"):
        ClaimAxesProfile(version="")
    with pytest.raises(TypeError, match="ClaimAxesProfile"):
        ClaimAxesDecoder(profile={"polarity": "attack"})
