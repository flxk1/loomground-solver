"""Wire-compatibility tests for the Versum claim-axes schema.

Two invariants:

- The *neutral* default service must never silently reject a claim-axes
  candidate inside a ``complete`` result: an unknown required schema surfaces
  as a request-level ``escalate`` through the error taxonomy.
- A *composed* service with the two-stage adapter (``ClaimAxesDecoder``)
  installed accepts a conforming claim-axes request.
"""
import hashlib

from loomground_solver.service import default_service

CLAIM_AXES_SCHEMA = "loomground.versum.claim-axes/v1"
_TEXT = "Controllers must notify the authority within 72 hours."


def claim_axes_request(axes=None):
    """A wire request shaped exactly as Versum's ``candidate_from_claim`` emits it."""
    digest = "sha256:" + hashlib.sha256(_TEXT.encode()).hexdigest()
    axes = axes if axes is not None else {
        "predicate": "requires",
        "modality": "obligation",
        "polarity": "positive",
        "quantification": "universal",
        "domain": "data-protection",
    }
    return {
        "protocol": "reasoning.interop",
        "protocol_version": "1.0",
        "kind": "reasoning_request",
        "request_id": "req-claim-axes-1",
        "problem": {"question": "Which grounded claims survive verification?"},
        "candidates": [{
            "candidate_id": "claim-1",
            "claim": _TEXT,
            "evidence": [{"source_id": "urn:lex:eu:reg:2016:679:art:33",
                          "item_id": "claim-1", "content_digest": digest}],
            "structural_evidence": {"schema": CLAIM_AXES_SCHEMA, "axes": axes},
            "producer": "loomground-versum",
            "producer_version": "0.1.0",
        }],
        "solver_profile": "generic",
        "required_capabilities": [],
        "extensions": {"inline_evidence": [
            {"source_id": "urn:lex:eu:reg:2016:679:art:33",
             "item_id": "claim-1", "content": _TEXT},
        ]},
    }


def test_neutral_default_service_escalates_claim_axes_request():
    result = default_service().verify(claim_axes_request())
    assert result["status"] == "escalate"
    # No silent per-candidate rejection: the schema gap is a request-level
    # outcome, not a verdict on the candidate's validity.
    assert result["rejected"] == {}
    assert result["accepted"] == []
    assert result["undecided"] == []
    assert result["trace"]["errors"] == [{
        "code": "unsupported_structural_schema",
        "scope": "request",
        "message": "no installed structural compiler for "
                   "'loomground.versum.claim-axes/v1'",
        "schema": CLAIM_AXES_SCHEMA,
        "candidate_ids": ["claim-1"],
    }]


def test_composed_service_accepts_conforming_claim_axes_request():
    # The composed service installs the Solver-side Versum decoder; the
    # neutral default (previous test) stays decoder-free.
    from loomground_solver.adapters.versum import ClaimAxesDecoder

    service = default_service(compilers=[ClaimAxesDecoder()])
    result = service.verify(claim_axes_request())
    assert result["status"] == "complete"
    assert result["accepted"] == ["claim-1"]
    assert result["rejected"] == {}
