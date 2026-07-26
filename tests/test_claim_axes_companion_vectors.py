"""Differential conformance against the claim-axes companion vectors.

The canonical vectors live in the language repo
(``standard/companions/claim-axes/vectors``); ``tests/fixtures/claim_axes_vectors``
is the versioned copy this repo vendors per ADR 002. The Solver's
``ClaimAxesDecoder`` is one of the companion's two independent implementations:
it must accept every valid record and reject every invalid one.
"""
import json
from pathlib import Path

import pytest

from loomground_solver.adapters.versum import ClaimAxesDecoder
from loomground_solver.interop import Candidate

VECTORS = Path(__file__).resolve().parent / "fixtures" / "claim_axes_vectors"


def _vectors():
    manifest = json.loads((VECTORS / "manifest.json").read_text())
    return [json.loads((VECTORS / name).read_text()) for name in manifest["vectors"]]


def _candidate(record) -> Candidate:
    return Candidate(candidate_id="claim-1", claim="Alpha is supported.",
                     evidence=(), structural_evidence=record)


@pytest.mark.parametrize("vector", _vectors(), ids=lambda v: v["name"])
def test_decoder_reproduces_every_companion_vector(vector):
    decoder = ClaimAxesDecoder()
    if vector["valid"]:
        compiled = decoder.compile(_candidate(vector["record"]))
        assert compiled["pairs"], vector["description"]
    else:
        with pytest.raises(ValueError):
            decoder.compile(_candidate(vector["record"]))


def test_vendored_copy_matches_the_canonical_vectors_when_present():
    canonical = (Path(__file__).resolve().parents[2] / "loomground-governance"
                 / "standard" / "companions" / "claim-axes" / "vectors")
    if not canonical.is_dir():
        pytest.skip("language repo not available")
    for path in sorted(VECTORS.glob("*.json")):
        assert (canonical / path.name).read_text() == path.read_text(), (
            f"{path.name} drifted from the canonical companion copy")
