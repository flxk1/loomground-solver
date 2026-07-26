# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Evidence-bearing authorization, versioning and rollback records."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Mapping

from .contracts import (ArtifactVersion, ImprovementProposal, ProposalStatus,
                        RollbackRecord)


def _digest(value: Mapping[str, Any]) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def authorize(proposal: ImprovementProposal, authorization_ref: str
              ) -> ImprovementProposal:
    """Record external authorization only after a complete passing evaluation."""
    if proposal.status is not ProposalStatus.EVALUATED:
        raise ValueError("only an evaluated proposal can be authorized")
    if not proposal.evaluation.get("eligible"):
        raise ValueError("proposal evaluation is not promotion-eligible")
    if not authorization_ref.strip():
        raise ValueError("authorization_ref is required")
    return replace(proposal, status=ProposalStatus.AUTHORIZED,
                   authorization_ref=authorization_ref)


def promote(proposal: ImprovementProposal, artifact: Mapping[str, Any], *,
            version_id: str, predecessor: str = "") -> tuple[ImprovementProposal,
                                                               ArtifactVersion]:
    """Create a version record; deployment remains a host responsibility."""
    if proposal.status is not ProposalStatus.AUTHORIZED or not proposal.authorization_ref:
        raise ValueError("promotion requires an externally authorized proposal")
    if not version_id.strip():
        raise ValueError("version_id is required")
    version = ArtifactVersion(version_id, proposal.proposal_id, _digest(artifact),
                              proposal.authorization_ref, predecessor)
    return replace(proposal, status=ProposalStatus.PROMOTED), version


def rollback(current: ArtifactVersion, target: ArtifactVersion, *,
             authorization_ref: str, evidence_refs) -> RollbackRecord:
    """Record an authorized rollback request without mutating deployed artifacts."""
    evidence = tuple(sorted(set(str(x) for x in evidence_refs if str(x))))
    if not authorization_ref.strip() or not evidence:
        raise ValueError("rollback requires authorization and evidence")
    seed = json.dumps([current.version_id, target.version_id, authorization_ref,
                       evidence], separators=(",", ":"))
    rollback_id = "rollback:" + hashlib.sha256(seed.encode()).hexdigest()[:16]
    return RollbackRecord(rollback_id, current.version_id, target.version_id,
                          authorization_ref, evidence)


class JsonlVersionRegistry:
    """Append-only version/rollback evidence registry, isolated by scope."""

    def __init__(self, root):
        self.root = Path(root)

    def append(self, scope_id: str, record: ArtifactVersion | RollbackRecord) -> None:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in scope_id)
        path = self.root / f"{safe or 'default'}.versions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {"kind": "rollback" if isinstance(record, RollbackRecord) else "version",
                **asdict(record)}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n")

    def load(self, scope_id: str) -> tuple[ArtifactVersion | RollbackRecord, ...]:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in scope_id)
        path = self.root / f"{safe or 'default'}.versions.jsonl"
        if not path.exists():
            return ()
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = json.loads(line)
            kind = raw.pop("kind")
            if kind == "rollback":
                raw["evidence_refs"] = tuple(raw["evidence_refs"])
                out.append(RollbackRecord(**raw))
            else:
                out.append(ArtifactVersion(**raw))
        return tuple(out)
