import hashlib
import json

import pytest

from loomground_solver.handler import UniversalHandler
from loomground_solver.interop import ReasoningRequest
from loomground_solver.service import default_service
from loomground_solver.validation import ValidationError


def request(*, candidates=None, required=(), profile="generic"):
    texts = {"a": "Alpha is supported.", "b": "Beta is supported."}
    candidates = candidates or [candidate("a", texts["a"])]
    evidence = [
        {"source_id": f"source-{key}", "item_id": key, "content": text}
        for key, text in texts.items()
    ]
    return {
        "protocol": "reasoning.interop",
        "protocol_version": "1.0",
        "kind": "reasoning_request",
        "request_id": "req-1",
        "problem": {"question": "Which claims survive verification?"},
        "candidates": candidates,
        "solver_profile": profile,
        "required_capabilities": list(required),
        "extensions": {"inline_evidence": evidence},
    }


def candidate(cid, claim, *, attacks=(), schema="reasoning.edges/v1", digest=None):
    content = {"a": "Alpha is supported.", "b": "Beta is supported."}.get(cid, claim)
    digest = digest or "sha256:" + hashlib.sha256(content.encode()).hexdigest()
    return {
        "candidate_id": cid,
        "claim": claim,
        "evidence": [{"source_id": f"source-{cid}", "item_id": cid,
                      "content_digest": digest}],
        "structural_evidence": {"schema": schema, "attacks": list(attacks)},
    }


def test_standalone_service_verifies_inline_evidence_deterministically():
    wire = request(required=("signed-replay",))
    first = default_service().verify(wire)
    second = default_service().verify(wire)
    assert first["status"] == "complete"
    assert first["accepted"] == ["a"]
    assert first["signature"] == second["signature"]
    assert first["trace"]["evidence"][0]["verified"] is True
    assert first["trace"]["fingerprint"]["version"] == "fp-2"


def test_mutual_attack_is_bounded_and_escalated():
    wire = request(candidates=[
        candidate("a", "Alpha is supported.", attacks=(("a", "b"),)),
        candidate("b", "Beta is supported.", attacks=(("b", "a"),)),
    ])
    result = default_service().verify(wire)
    assert result["status"] == "escalate"
    assert result["accepted"] == []
    assert result["undecided"] == ["a", "b"]


@pytest.mark.parametrize("change, reason", [
    ({"digest": "sha256:" + "0" * 64}, "evidence verification failed"),
    ({"claim": "A fabricated claim."}, "does not match"),
])
def test_untrusted_candidate_failures_are_rejected(change, reason):
    item = candidate("a", change.get("claim", "Alpha is supported."),
                     schema=change.get("schema", "reasoning.edges/v1"),
                     digest=change.get("digest"))
    result = default_service().verify(request(candidates=[item]))
    assert result["accepted"] == []
    assert reason in result["rejected"]["a"]


def test_unknown_structural_schema_escalates_the_request_without_a_verdict():
    item = candidate("a", "Alpha is supported.", schema="vendor.private/v9")
    result = default_service().verify(request(candidates=[item]))
    assert result["status"] == "escalate"
    assert result["accepted"] == result["undecided"] == []
    assert result["rejected"] == {}
    assert result["trace"]["errors"][0]["code"] == "unsupported_structural_schema"
    assert result["trace"]["errors"][0]["schema"] == "vendor.private/v9"


def test_external_provider_snapshot_mismatch_escalates_before_verification():
    class Provider:
        graph_version = "sha256:" + "1" * 64

        def resolve(self, ref):
            raise AssertionError("snapshot mismatch must stop before resolution")

        def verify(self, ref):
            raise AssertionError("snapshot mismatch must stop before verification")

    item = candidate("a", "Alpha is supported.")
    item["evidence"][0]["graph_version"] = "sha256:" + "2" * 64
    typed = ReasoningRequest.from_dict(request(candidates=[item]))
    result = UniversalHandler(evidence_provider=Provider())(typed)
    assert result.status == "escalate"
    assert result.rejected == {}
    assert result.trace["errors"][0]["code"] == "evidence_snapshot_mismatch"


def test_missing_snapshot_id_escalates_with_a_distinct_reason():
    class Provider:
        graph_version = "sha256:" + "1" * 64

        def resolve(self, ref):
            raise AssertionError("missing snapshot id must stop before resolution")

        def verify(self, ref):
            raise AssertionError("missing snapshot id must stop before verification")

    item = candidate("a", "Alpha is supported.")
    item["evidence"][0]["graph_version"] = ""
    typed = ReasoningRequest.from_dict(request(candidates=[item]))
    result = UniversalHandler(evidence_provider=Provider())(typed)
    assert result.status == "escalate"
    assert result.rejected == {}
    assert result.trace["errors"][0]["code"] == "evidence_snapshot_missing"


def test_missing_and_stale_snapshot_ids_are_reported_as_separate_errors():
    class Provider:
        graph_version = "sha256:" + "1" * 64

        def resolve(self, ref):
            raise AssertionError("snapshot gaps must stop before resolution")

        def verify(self, ref):
            raise AssertionError("snapshot gaps must stop before verification")

    absent = candidate("a", "Alpha is supported.")
    absent["evidence"][0]["graph_version"] = ""
    outdated = candidate("b", "Beta is supported.")
    outdated["evidence"][0]["graph_version"] = "sha256:" + "2" * 64
    typed = ReasoningRequest.from_dict(request(candidates=[absent, outdated]))
    result = UniversalHandler(evidence_provider=Provider())(typed)
    assert result.status == "escalate"
    codes = [error["code"] for error in result.trace["errors"]]
    assert codes == ["evidence_snapshot_missing", "evidence_snapshot_mismatch"]
    assert result.trace["errors"][0]["references"][0]["candidate_id"] == "a"
    assert result.trace["errors"][1]["references"][0]["candidate_id"] == "b"


def test_external_provider_and_compiler_are_injected_without_graph_dependency():
    class Provider:
        def resolve(self, ref):
            return {"content": "Claim from another graph."}

        def verify(self, ref):
            return True

    class Compiler:
        def supports(self, schema):
            return schema == "other.graph/v1"

        def compile(self, candidate):
            return {"pairs": [], "attacks": [], "schema": "other.graph/v1"}

    item = candidate("a", "Claim from another graph.", schema="other.graph/v1")
    typed = ReasoningRequest.from_dict(request(candidates=[item]))
    result = UniversalHandler(evidence_provider=Provider(), compilers=[Compiler()])(typed)
    assert result.accepted == ("a",)


def test_unknown_attack_target_is_rejected_not_executed():
    item = candidate("a", "Alpha is supported.", attacks=(("a", "missing"),))
    result = default_service().verify(request(candidates=[item]))
    assert "unknown candidates" in result["rejected"]["a"]


def test_envelope_invariants_fail_closed():
    wire = request()
    wire["candidates"].append(dict(wire["candidates"][0]))
    with pytest.raises(ValidationError, match="unique"):
        default_service().verify(wire)


def test_profile_selection_is_versioned():
    result = default_service().verify(request(profile="generic@1"))
    assert result["extensions"]["profile"] == {"id": "generic", "version": "1"}
    with pytest.raises(ValueError, match="incompatible"):
        default_service().verify(request(profile="generic@2"))


def test_result_is_json_serializable():
    json.dumps(default_service().verify(request()))


def test_loomground_route_uses_the_neutral_protocol_and_signed_replay():
    wire = {
        "protocol": "reasoning.interop", "protocol_version": "1.0",
        "kind": "reasoning_request", "request_id": "lg-1",
        "problem": {
            "language": "loomground", "language_version": "0.8.2",
            "source": (
                "actor bot\ngate decide grant bot\n"
                "cord bot -> decide\ncord decide -> master\n"
            ),
            "transport": {"activations": [{
                "actor": "bot", "source": "decide", "token": {
                    "id": "action-1", "kind": "act", "risk": "low",
                    "party": "deployer", "provenance": []},
            }]},
        },
        "candidates": [], "solver_profile": "loomground@0.8.2",
        "required_capabilities": ["loomground-governance", "signed-replay"],
    }
    result = default_service().verify(wire)
    assert result["accepted"] == ["action-1"]
    assert result["signature"]
    assert result["extensions"] == {
            "language": "loomground", "language_version": "0.8.2"}


def test_loomground_protocol_rejects_unknown_version_and_candidates():
    wire = {
        "protocol": "reasoning.interop", "protocol_version": "1.0",
        "kind": "reasoning_request", "request_id": "lg-bad",
        "problem": {"language": "loomground", "language_version": "9",
                    "source": "gate g\ncord g -> master\n"},
        "candidates": [],
    }
    with pytest.raises(ValueError, match="unsupported Loomground version"):
        default_service().verify(wire)
    wire["candidates"] = [candidate("a", "Alpha is supported.")]
    with pytest.raises(ValidationError, match="do not accept candidates"):
        default_service().verify(wire)
