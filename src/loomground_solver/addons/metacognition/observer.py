# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Read-only observation and deterministic recurring-gap proposals.

A minimal, read-only take on execution reflection and recurring-gap
detection: it observes a signed run record and proposes improvements
deterministically. It excludes any execution runtime, knowledge-graph
mutation, model calls, and auto-approval — those stay host-side, outside this
package.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Callable, Iterable, Mapping

from .contracts import (ImprovementKind, ImprovementProposal, Observation,
                        SignedRunRecord)

_STOPWORDS = frozenset({
    "that", "this", "what", "when", "where", "which", "with", "from",
    "have", "been", "were", "would", "could", "should", "about", "into",
    "more", "some", "than", "them", "then", "they", "their", "there",
})


def signals(text: str, *, limit: int = 15) -> tuple[str, ...]:
    """Extract stable structural tokens without invoking a model."""
    out, seen = [], set()
    for token in re.findall(r"[A-Za-z0-9§]+(?:[-_.][A-Za-z0-9§]+)*", text):
        token = token.lower()
        if len(token) <= 3 or token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        out.append(token)
        if len(out) == limit:
            break
    return tuple(out)


def observe_record(record: SignedRunRecord, *, verifier,
                   downstream_outcome: str | None = None) -> Observation:
    """Project the stable typed record after host replay verification."""
    verify = verifier.verify if hasattr(verifier, "verify") else verifier
    if not verify(record):
        raise ValueError("run record signature/replay verification failed")
    if not record.run_id or not record.replay_digest:
        raise ValueError("observation requires run_id and replay digest/signature")
    return Observation(record.run_id, record.replay_digest, record.decision,
                       tuple(sorted(record.gaps)), downstream_outcome, record.scope_id)


def observe(record: Mapping, *, verifier: Callable[[Mapping], bool],
            downstream_outcome: str | None = None,
            scope_id: str = "default") -> Observation:
    """Compatibility mapping facade over :func:`observe_record`."""
    run_id = str(record.get("run_id", ""))
    replay_digest = str(record.get("replay_digest") or record.get("signature") or "")
    typed = SignedRunRecord(run_id, replay_digest,
                            str(record.get("decision", "undecided")),
                            tuple(str(x) for x in record.get("gaps", ())), scope_id,
                            dict(record))
    return observe_record(typed, verifier=lambda _typed: verifier(record),
                          downstream_outcome=downstream_outcome)


def recurring_gap_proposals(observations: Iterable[Observation], *,
                            minimum_runs: int = 3) -> tuple[ImprovementProposal, ...]:
    """Group identical structural gap signatures and emit draft proposals only."""
    groups = defaultdict(list)
    for observation in observations:
        for gap in observation.gaps:
            key = "|".join(signals(gap)) or gap.strip().lower()
            groups[(observation.scope_id, key)].append((observation, gap))
    proposals = []
    for (scope_id, key), occurrences in sorted(groups.items()):
        run_ids = tuple(sorted({item.run_id for item, _gap in occurrences}))
        if len(run_ids) < minimum_runs:
            continue
        seed = json.dumps([scope_id, key, run_ids], separators=(",", ":"))
        proposal_id = "proposal:" + hashlib.sha256(seed.encode()).hexdigest()[:16]
        examples = tuple(dict.fromkeys(gap for _item, gap in occurrences))[:3]
        proposals.append(ImprovementProposal(
            proposal_id=proposal_id,
            kind=ImprovementKind.TEST,
            motivating_runs=run_ids,
            proposed_change={"gap_pattern": key, "examples": examples,
                             "required_action": "add-regression-and-evaluate"},
            scope_id=scope_id,
            pattern_key=key,
        ))
    return tuple(proposals)
