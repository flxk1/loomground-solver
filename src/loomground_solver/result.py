"""Canonical protocol result and replay construction."""
from __future__ import annotations

import json

from .fingerprint import fingerprint
from .interop import ReasoningResult
from .replay import HashSigner


def _signature(trace, signer=None):
    payload = json.dumps(trace, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return (signer or HashSigner()).sign(payload)


def _context(request):
    context = request.extensions.get("context_snapshot")
    return dict(context) if context is not None else None


def build_result(request, decision, *, pairs=(), receipts=(), configuration=None,
                 signer=None, verifier="loomground-solver", verifier_version="0.1.0"):
    rejected = {r["id"]: r["reason"] for r in decision.rejected}
    fp = fingerprint(filters=("logical_form", "attack_topology", "statistics"),
                     pairs=list(pairs), pack=getattr(configuration, "rule_pack", None),
                     decision=decision)
    trace = {
        "request_id": request.request_id,
        "problem": dict(request.problem),
        "profile": {"id": getattr(configuration, "id", request.solver_profile),
                    "version": getattr(configuration, "version", "")},
        "evidence": list(receipts),
        "decision": decision.to_dict(),
        "fingerprint": fp,
    }
    if _context(request) is not None:
        trace["context_snapshot"] = _context(request)
    signature = _signature(trace, signer)
    status = "escalate" if decision.undecided else "complete"
    return ReasoningResult(
        request_id=request.request_id,
        status=status,
        accepted=tuple(sorted(decision.accepted)),
        undecided=tuple(sorted(decision.undecided)),
        rejected=rejected,
        trace=trace,
        verifier=verifier,
        verifier_version=verifier_version,
        signature=signature,
        extensions={"profile": trace["profile"]},
    )


def build_request_escalation(request, errors, *, signer=None,
                             verifier="loomground-solver",
                             verifier_version="0.1.0"):
    """Return an honest request-level escalation before candidate adjudication.

    ``errors`` contains structured taxonomy records for unsupported contract
    semantics or snapshot scope. Candidate decision partitions stay empty:
    failure to understand the request is not evidence against a candidate.
    """
    trace = {
        "request_id": request.request_id,
        "problem": dict(request.problem),
        "errors": [dict(error) for error in errors],
    }
    if _context(request) is not None:
        trace["context_snapshot"] = _context(request)
    return ReasoningResult(
        request_id=request.request_id,
        status="escalate",
        trace=trace,
        verifier=verifier,
        verifier_version=verifier_version,
        signature=_signature(trace, signer),
        extensions={"outcome": "request_escalation"},
    )


def build_loomground_result(request, route, *, signer=None,
                            verifier="loomground-solver", verifier_version="0.1.0"):
    """Adapt a Loomground route outcome to the neutral protocol result."""
    trace = {
        "request_id": request.request_id,
        "problem": {"language": "loomground",
                    "language_version": route["language_version"]},
        "loomground": route["trace"],
    }
    if _context(request) is not None:
        trace["context_snapshot"] = _context(request)
    return ReasoningResult(
        request_id=request.request_id,
        status=route["status"],
        accepted=tuple(route["accepted"]),
        undecided=tuple(route["undecided"]),
        rejected=dict(route["rejected"]),
        trace=trace,
        verifier=verifier,
        verifier_version=verifier_version,
        signature=_signature(trace, signer),
        extensions={"language": "loomground",
                    "language_version": route["language_version"]},
    )
