import json

import pytest

from loomground_solver.interop import (
    Candidate, EvidenceRef, ProtocolManifest, ReasoningRequest, ReasoningResult,
    missing_capabilities,
)
from loomground_solver.service import SolverService


def request():
    ref = EvidenceRef("urn:any:source:1", "claim-1", 4, 19,
                      "sha256:abc", "graph-7", {"partition": "a"})
    candidate = Candidate("c1", "A grounded claim", (ref,),
                          {"schema": "example.edges/v1", "edges": []},
                          "example-graph", "2.0", {"bm25": 0.8})
    return ReasoningRequest("r1", {"text": "Is the claim supported?"}, (candidate,),
                            required_capabilities=("candidate-adjudication",))


def test_wire_roundtrip_is_json_safe():
    wire = json.loads(json.dumps(request().to_dict()))
    assert ReasoningRequest.from_dict(wire) == request()
    assert wire["protocol"] == "reasoning.interop"


def test_version_mismatch_refuses_comparison():
    wire = request().to_dict()
    wire["protocol_version"] = "99"
    with pytest.raises(ValueError, match="incompatible"):
        ReasoningRequest.from_dict(wire)


def test_capability_negotiation_is_explicit():
    m = ProtocolManifest("x", "1", ("verifier",), ("a",))
    assert missing_capabilities(m, ("a", "b")) == ("b",)


def test_service_dispatches_without_knowing_the_graph():
    def handler(req):
        return ReasoningResult(req.request_id, "complete", accepted=("c1",),
                               verifier="test-solver", verifier_version="1")

    service = SolverService(handler, implementation="test-solver",
                            capabilities=("candidate-adjudication",))
    result = ReasoningResult.from_dict(service.verify(request().to_dict()))
    assert result.accepted == ("c1",)


def test_service_escalates_unsupported_capability_without_calling_handler():
    service = SolverService(lambda req: pytest.fail("must not dispatch"), capabilities=())
    result = ReasoningResult.from_dict(service.verify(request().to_dict()))
    assert result.status == "escalate"
    assert result.trace["missing"] == ["candidate-adjudication"]

