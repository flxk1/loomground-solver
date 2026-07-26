# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The problem-solving KG — the pure, corpus-free subset.

A case record is a data structure mirroring legal method:

    PROBLEM (clause/question) → GROUNDS & CHAIN (anchored norm-spans with
    coverage receipts; the subsumption ladder) → RESOLUTION (a determinate
    answer, or the decision surface with the recorded, originated choice).

This module holds the pure pieces: the ``Ground``/``Fact``/``CaseRecord``
dataclasses and the ``project_pairs`` projection into the dimensioned pair/edge
format, so a case composes with the 5D machinery. Building cases from a corpus
(``build_case`` and friends) needs the rule registry / extractor — corpus-coupled
code that arrives through injected ports in the host, never imported here.
Pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Ground:
    pinpoint: str               # "GDPR Art. 17(3)" / "§ 147 AO"
    text: str = ""              # the norm-span text (when held in the registry)
    entity: str = ""            # instrument code (gdpr, ao…)
    receipted: bool = True      # a read-receipt exists for this room
    condition: str = ""         # the norm's Tatbestand (extractor `condition`)
    consequence: str = ""       # the norm's Rechtsfolge (extractor `action`)
    exception: str = ""         # the norm's own carve-out ("unless …") — a norm
                                # is not read until its exception is examined

    def to_dict(self) -> dict:
        return {"pinpoint": self.pinpoint, "text": self.text,
                "entity": self.entity, "receipted": self.receipted,
                "condition": self.condition, "consequence": self.consequence,
                "exception": self.exception}


@dataclass
class Fact:
    """An evidenced factual premise — the FACTS column of the universal pattern.
    Same receipt mechanics as a Ground, anchored to the world/document rather
    than to an instrument (reasoning contract R1)."""
    text: str
    source: str = ""            # document / exhibit / statement the fact comes from

    def to_dict(self) -> dict:
        return {"text": self.text, "source": self.source}


@dataclass
class CaseRecord:
    problem: dict               # {text, document, pinpoint}
    grounds: list[Ground]
    chain: list[dict]           # [{step, text, warrant?}] — step vocab set by `profile`
    gaps: list[str]             # required rooms with NO receipt — reported, never hidden
    resolution: dict            # {"type":"determinate","answer":…} |
                                # {"type":"residual","surface":…,"choice":…}
    coverage: float = 1.0       # required-room recall (receipted / required)
    facts: list[Fact] = field(default_factory=list)      # evidenced premises (R1)
    actions: list[dict] = field(default_factory=list)    # [{obligation, actor, deadline, source_norm}] (R5)
    profile: str = "legal-de"   # render vocabulary: legal-de | legal-irac | frma | generic
    contract: dict = field(default_factory=dict)         # reasoning-contract report
    waivers: list[dict] = field(default_factory=list)    # gaps OWNED by a human (signed)

    def to_dict(self) -> dict:
        return {"problem": self.problem,
                "grounds": [g.to_dict() for g in self.grounds],
                "chain": self.chain, "gaps": self.gaps,
                "resolution": self.resolution, "coverage": self.coverage,
                "facts": [f.to_dict() for f in self.facts],
                "actions": self.actions, "profile": self.profile,
                "contract": self.contract, "waivers": self.waivers}


def _norm_spans_for(registry, instrument_codes: set) -> list[dict]:
    """The per-article norm-spans the registry holds for the cited instruments."""
    out = []
    for r in registry.workspace_items():
        if r.get("kind") != "norm":
            continue
        if any(a["entity"] in instrument_codes for a in r.get("anchors", [])):
            out.append(r)
    return out


# ── projection into the dimensioned pair/edge format ──────────────────────────

def project_pairs(case: CaseRecord, *, case_id: str = "case") -> list[dict]:
    """Emit the case as dimensioned pairs so it composes with the 5D machinery:
    problem —grounded_in(causal)→ each ground; chain steps —then(causal)→ next;
    problem —resolved_by/escalated_to(intentional)→ resolution; gaps as
    structural edges to an explicit GAP node (gaps are first-class, never hidden)."""
    pid = f"problem:{case_id}"
    edges = []
    nodes = [{"id": pid, "kind": "problem", "label": case.problem["text"][:80]}]
    for i, g in enumerate(case.grounds):
        gid = f"ground:{case_id}:{i}"
        # a legal norm IS a problem→solution pair: Tatbestand → Rechtsfolge.
        # The agreed schema, verbatim — condition in the problem slot,
        # consequence in the solution slot, pinpoint as label. No template
        # phrasing: wrapping the condition in a question adds tokens, not
        # meaning.
        nodes.append({"id": gid, "kind": "ground", "label": g.pinpoint,
                      "norm_problem": g.condition or g.pinpoint,
                      "norm_solution": g.consequence or g.text})
        edges.append({"subject": pid, "predicate": "grounded_in", "object": gid,
                      "dimension": "causal", "note": g.pinpoint})
    for i, step in enumerate(case.chain):
        sid = f"step:{case_id}:{i}"
        nodes.append({"id": sid, "kind": "chain-step", "label": step.get("step", "")})
        prev = f"step:{case_id}:{i-1}" if i else pid
        edges.append({"subject": prev, "predicate": "then", "object": sid,
                      "dimension": "causal", "note": step.get("text", "")[:120]})
    for room in case.gaps:
        gid = f"gap:{case_id}:{room}"
        nodes.append({"id": gid, "kind": "gap", "label": f"GAP: {room}"})
        edges.append({"subject": pid, "predicate": "required_room_missing",
                      "object": gid, "dimension": "structural",
                      "note": "no read-receipt for a required room"})
    rid = f"resolution:{case_id}"
    rkind = case.resolution["type"]
    rlabel = (case.resolution.get("answer", "")[:80] if rkind == "determinate"
              else ("DECIDED: " + case.resolution["choice"]["chosen_label"]
                    if rkind == "residual" and case.resolution.get("choice")
                    else "OPEN DECISION"))
    nodes.append({"id": rid, "kind": "resolution", "label": rlabel})
    edges.append({"subject": pid,
                  "predicate": "resolved_by" if rkind == "determinate" else "escalated_to",
                  "object": rid, "dimension": "intentional",
                  "note": case.resolution.get("answer", "") or rkind})
    # Pair semantics, not a wrapper: where a node has real problem→solution
    # structure (a norm: Tatbestand → Rechtsfolge), use it. Structural nodes
    # (chain steps, gaps) keep the label in both slots — they are index
    # entries, and pretending otherwise would be invented meaning.
    return [{
        "id": n["id"],
        "problem": {"id": n["id"] + "-p", "scope": "problem-kg", "type": n["kind"],
                    "summary": n.get("norm_problem", n["label"]), "facets": {}},
        "solution": {"id": n["id"], "problem_id": n["id"] + "-p",
                     "body": n.get("norm_solution", n["label"]),
                     "body_format": "kg-node", "authority_tier": 1, "confidence": 1.0},
        "edges": [e for e in edges if e["subject"] == n["id"]],
    } for n in nodes]
