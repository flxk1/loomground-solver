# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Rung-4 replay tests: deterministic re-derivation, provenance shape, content
signature, and tamper detection (record OR inputs)."""
from __future__ import annotations

from loomground_solver import (
    Scenario, Norm, derive, LEX_CONFLICT_PACK,
    HashSigner, provenance, verify_trace, sign, verify, Signer,
)


def _scenario():
    return Scenario("w", norms=[
        Norm("act", "obligatory", source="general", specificity=0),
        Norm("act", "prohibited", source="specific", specificity=5),
    ], edges=[{"id": "e", "edges": [
        {"subject": "A", "predicate": "causes", "object": "B", "dimension": "causal"}]}])


def test_hashsigner_satisfies_the_port_and_roundtrips():
    s = HashSigner()
    assert isinstance(s, Signer)
    sig = s.sign(b"hello")
    assert sig.startswith("sha256:") and s.verify(b"hello", sig)
    assert not s.verify(b"tampered", sig)


def test_replay_is_deterministic():
    sc = _scenario()
    trace = derive(sc, pack=LEX_CONFLICT_PACK).trace()
    # re-deriving the same scenario reproduces the identical trace
    assert verify_trace(sc, trace, pack=LEX_CONFLICT_PACK)


def test_tampered_trace_fails_replay():
    sc = _scenario()
    trace = derive(sc, pack=LEX_CONFLICT_PACK).trace()
    trace["acts"]["act"]["verdict"] = "permitted"      # doctor the record
    assert not verify_trace(sc, trace, pack=LEX_CONFLICT_PACK)


def test_signature_verifies_by_rederiving_from_inputs():
    sc = _scenario()
    result = derive(sc, pack=LEX_CONFLICT_PACK)
    signature = sign(result)
    assert verify(sc, signature, pack=LEX_CONFLICT_PACK)


def test_tampered_inputs_break_the_signature():
    sc = _scenario()
    signature = sign(derive(sc, pack=LEX_CONFLICT_PACK))
    # swap the specificity so the derivation now resolves the other way
    sc.norms[1] = Norm("act", "prohibited", source="specific", specificity=0)
    assert not verify(sc, signature, pack=LEX_CONFLICT_PACK)


def test_provenance_has_prov_shape():
    res = derive(_scenario(), pack=LEX_CONFLICT_PACK)
    prov = provenance(res)
    assert prov["prov:agent"]["id"] == "loomground-solver"
    kinds = {a["kind"] for a in prov["prov:activities"]}
    assert "defeat" in kinds          # the lex-specialis defeat is recorded as an activity
