"""Central invariants for the vendor-neutral reasoning protocol."""
from __future__ import annotations

import re

from .interop import ReasoningRequest, ReasoningResult

_DIGEST = re.compile(r"^(sha256):[0-9a-f]{64}$")


class ValidationError(ValueError):
    pass


def validate_request(request: ReasoningRequest) -> None:
    if not request.request_id.strip():
        raise ValidationError("request_id is required")
    if not isinstance(request.problem, dict) or not request.problem:
        raise ValidationError("problem must be a non-empty object")
    context = request.extensions.get("context_snapshot")
    if context is not None:
        if not isinstance(context, dict):
            raise ValidationError("context_snapshot extension must be an object")
        if not str(context.get("snapshot_id", "")).strip():
            raise ValidationError("context snapshot_id is required")
        if not _DIGEST.fullmatch(str(context.get("digest", "")).lower()):
            raise ValidationError("context snapshot digest is malformed")
        if not str(context.get("created_at", "")).strip():
            raise ValidationError("context created_at is required")
        findings = context.get("findings", [])
        if not isinstance(findings, list) or not all(isinstance(x, dict) for x in findings):
            raise ValidationError("context findings must be a list of objects")
    route = request.problem.get("language") == "loomground"
    if route:
        source = request.problem.get("source")
        transport = request.problem.get("transport", {"activations": []})
        if not isinstance(source, str) or not source.strip():
            raise ValidationError("Loomground problem source must be non-empty text")
        if not isinstance(transport, dict):
            raise ValidationError("Loomground transport must be an object")
        if request.candidates:
            raise ValidationError("Loomground route requests do not accept candidates")
    elif not request.candidates:
        raise ValidationError("at least one candidate is required")
    ids = [c.candidate_id.strip() for c in request.candidates]
    if any(not cid for cid in ids):
        raise ValidationError("candidate_id is required")
    if len(set(ids)) != len(ids):
        raise ValidationError("candidate IDs must be unique")
    for candidate in request.candidates:
        if not candidate.claim.strip():
            raise ValidationError(f"candidate {candidate.candidate_id!r} has no claim")
        if not candidate.evidence:
            raise ValidationError(f"candidate {candidate.candidate_id!r} has no evidence")
        for ref in candidate.evidence:
            if not ref.source_id.strip():
                raise ValidationError("evidence source_id is required")
            if (ref.span_start is None) != (ref.span_end is None):
                raise ValidationError("evidence span must have both endpoints")
            if ref.span_start is not None:
                if not isinstance(ref.span_start, int) or not isinstance(ref.span_end, int):
                    raise ValidationError("evidence span endpoints must be integers")
                if not 0 <= ref.span_start < ref.span_end:
                    raise ValidationError("evidence span is invalid")
            if ref.content_digest and not _DIGEST.fullmatch(ref.content_digest.lower()):
                raise ValidationError("unsupported or malformed evidence digest")


def validate_result(request: ReasoningRequest, result: ReasoningResult, *,
                    implementation: str = "", implementation_version: str = "") -> None:
    if result.request_id != request.request_id:
        raise ValidationError("result request_id does not match request")
    if request.problem.get("language") == "loomground":
        submitted = {
            str((activation.get("token") or {}).get("id") or f"activation-{index + 1}")
            for index, activation in enumerate(
                request.problem.get("transport", {}).get("activations", [])
            )
        }
    else:
        submitted = {c.candidate_id for c in request.candidates}
    accepted, undecided, rejected = set(result.accepted), set(result.undecided), set(result.rejected)
    if not (accepted | undecided | rejected) <= submitted:
        raise ValidationError("result contains unknown candidate IDs")
    if accepted & undecided or accepted & rejected or undecided & rejected:
        raise ValidationError("result decision partitions overlap")
    if implementation and result.verifier != implementation:
        raise ValidationError("result verifier does not match service")
    if implementation_version and result.verifier_version != implementation_version:
        raise ValidationError("result verifier version does not match service")
    if "signed-replay" in request.required_capabilities and not result.signature:
        raise ValidationError("signed replay was required but no signature was returned")
