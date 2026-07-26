# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Explicit JSONL proposal store; no promotion behavior is implemented."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .contracts import ImprovementKind, ImprovementProposal, ProposalStatus


class JsonlProposalStore:
    def __init__(self, root):
        self.root = Path(root)

    def _path(self, scope_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in scope_id)
        return self.root / f"{safe or 'default'}.jsonl"

    def append(self, proposal: ImprovementProposal) -> None:
        """Append a draft/evaluated proposal; promotion is external."""
        if proposal.status in {ProposalStatus.PROMOTED, ProposalStatus.ROLLED_BACK}:
            raise ValueError("operational status changes require an external authority")
        path = self._path(proposal.scope_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = asdict(proposal)
        record["kind"] = proposal.kind.value
        record["status"] = proposal.status.value
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    def load(self, scope_id: str = "default") -> tuple[ImprovementProposal, ...]:
        path = self._path(scope_id)
        if not path.exists():
            return ()
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = json.loads(line)
            raw["kind"] = ImprovementKind(raw["kind"])
            raw["status"] = ProposalStatus(raw["status"])
            raw["motivating_runs"] = tuple(raw["motivating_runs"])
            change = raw.get("proposed_change", {})
            if isinstance(change.get("examples"), list):
                change["examples"] = tuple(change["examples"])
            out.append(ImprovementProposal(**raw))
        return tuple(out)
