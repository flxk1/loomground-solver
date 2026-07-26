import pytest

from loomground_solver.addons.world_model import (
    Belief, Freshness, interop_extension, make_snapshot,
)
from loomground_solver.service import default_service
from loomground_solver.validation import ValidationError

from test_universal_handler import request


def _snapshot(value="x"):
    return make_snapshot([
        Belief("b:1", {"value": value}, ("e:1",), "2025-01-01T00:00:00Z",
               freshness=Freshness.STALE)
    ], created_at="2026-07-19T00:00:00Z")


def test_context_identity_and_findings_are_signed_not_full_beliefs():
    wire = request()
    wire["extensions"]["context_snapshot"] = interop_extension(_snapshot())
    result = default_service().verify(wire)
    context = result["trace"]["context_snapshot"]
    assert context["digest"].startswith("sha256:")
    assert context["findings"][0]["kind"] == "context-freshness"
    assert "beliefs" not in context


def test_context_change_changes_result_signature_without_changing_decision():
    first, second = request(), request()
    first["extensions"]["context_snapshot"] = interop_extension(_snapshot("x"))
    second["extensions"]["context_snapshot"] = interop_extension(_snapshot("y"))
    a, b = default_service().verify(first), default_service().verify(second)
    assert a["accepted"] == b["accepted"] == ["a"]
    assert a["signature"] != b["signature"]


@pytest.mark.parametrize("context", [
    {},
    {"snapshot_id": "s", "digest": "bad", "created_at": "t", "findings": []},
    {"snapshot_id": "s", "digest": "sha256:" + "0" * 64,
     "created_at": "t", "findings": "bad"},
])
def test_malformed_context_extension_fails_closed(context):
    wire = request()
    wire["extensions"]["context_snapshot"] = context
    with pytest.raises(ValidationError):
        default_service().verify(wire)
