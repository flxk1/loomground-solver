# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Signed, replayable provenance for scenario derivations (rung 4).

A derivation is worth trusting only if you can re-run it and get the same answer,
and detect if the record was altered. This module:

  * renders a scenario result as a PROV-O-shaped trace (entities / activities /
    agent) — :func:`provenance`;
  * **replays** a derivation deterministically from its inputs and confirms the
    trace is identical — :func:`verify_trace`;
  * **signs** the canonical trace and verifies the signature by re-deriving from
    the inputs — :func:`sign` / :func:`verify` — so a tampered trace OR tampered
    inputs both fail.

Signing goes through the :class:`ports.Signer` port. The default
:class:`HashSigner` is a content digest (SHA-256); a host with a real key
(for example an Ed25519 audit chain) injects that. Pure stdlib."""
from __future__ import annotations

import hashlib
import json

from . import scenario as _scenario


class HashSigner:
    """Default :class:`ports.Signer`: a SHA-256 content digest. Not a secret-key
    signature — it makes tampering *detectable*, not *attributable*. Inject a
    real keyed host signer when attribution is required."""

    def sign(self, payload: bytes) -> str:
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def verify(self, payload: bytes, signature: str) -> bool:
        return self.sign(payload) == signature


def canonical_bytes(trace: dict) -> bytes:
    """Deterministic serialization of a trace (stable key order, no whitespace
    drift) so the same derivation always yields the same bytes."""
    return json.dumps(trace, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def provenance(result) -> dict:
    """A PROV-O-shaped view of the derivation: the derived facts are *entities*,
    each inference/defeat is an *activity* that used its premises and was
    associated with the solver *agent*."""
    activities = []
    for i in result.inferences:
        activities.append({
            "type": "prov:Activity", "kind": "compose",
            "used": [f"{e.get('subject')}->{e.get('object')}" for e in i.path],
            "generated": f"{i.subject}->{i.object}",
        })
    for a, r in sorted(result.acts.items()):
        for d in r.defeats:
            activities.append({
                "type": "prov:Activity", "kind": "defeat", "rule": d["rule"],
                "used": [d["winner"], d["loser"]], "generated": f"{a}:defeated({d['loser']})",
            })
        for c in r.collisions:
            activities.append({
                "type": "prov:Activity", "kind": "collision-escalated",
                "used": list(c), "generated": f"{a}:open",
            })
    return {
        "prov:agent": {"type": "prov:SoftwareAgent", "id": "loomground-solver"},
        "prov:entity": {"scenario": result.scenario},
        "prov:activities": activities,
    }


def verify_trace(scenario, trace: dict, *, pack=None) -> bool:
    """Replay: re-derive the scenario from its inputs and confirm the produced
    trace is identical to ``trace``. A record altered after the fact fails."""
    from .rulepacks import GENERIC_PACK
    fresh = _scenario.derive(scenario, pack=pack or GENERIC_PACK).trace()
    return canonical_bytes(fresh) == canonical_bytes(trace)


def sign(result, *, signer=None) -> str:
    """Sign the canonical trace of a scenario result."""
    signer = signer or HashSigner()
    return signer.sign(canonical_bytes(result.trace()))


def verify(scenario, signature: str, *, pack=None, signer=None) -> bool:
    """Re-derive ``scenario`` from its inputs and check ``signature`` against the
    freshly computed trace. Tampered inputs (different derivation) OR a forged
    signature both fail."""
    from .rulepacks import GENERIC_PACK
    signer = signer or HashSigner()
    fresh = _scenario.derive(scenario, pack=pack or GENERIC_PACK)
    return signer.verify(canonical_bytes(fresh.trace()), signature)


def contextual_trace(result, snapshot) -> dict:
    """Bind an immutable context identity to a trace without changing reasoning."""
    if not snapshot.digest:
        raise ValueError("context snapshot must have a canonical digest")
    return {
        "trace": result.trace(),
        "context": {
            "snapshot_id": snapshot.snapshot_id,
            "digest": snapshot.digest,
            "created_at": snapshot.created_at,
        },
    }


def sign_contextual(result, snapshot, *, signer=None) -> str:
    signer = signer or HashSigner()
    return signer.sign(canonical_bytes(contextual_trace(result, snapshot)))


def verify_contextual(scenario, snapshot, signature: str, *, pack=None,
                      signer=None) -> bool:
    """Re-derive and verify both reasoning output and exact context snapshot."""
    from .rulepacks import GENERIC_PACK
    signer = signer or HashSigner()
    fresh = _scenario.derive(scenario, pack=pack or GENERIC_PACK)
    return signer.verify(canonical_bytes(contextual_trace(fresh, snapshot)), signature)
