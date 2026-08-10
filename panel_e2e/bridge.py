# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The versum→solver bridge — ingest a case's source text through the real
planes and reconstruct a solver Scenario from what was PERSISTED.

Every contract here was learned from the planes' own refusals (Phase-0 spike):
the write envelope's exact key sets and identifier grammar, the nD descriptor
from the deontic plane's canon, and the persistence re-keying
(kind→node_type, id→node_id, payload→properties). Anything that does not
reconstruct is REPORTED as a gap, never guessed.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from loomground_ingest import DeonticIngester
from loomground_ingest.pipeline import ingest_text
from loomground_ingest.registry import IngesterRegistry
from loomground_ingest.writer import versum_writer
from versum import load_dimensioned_subgraphs
from versum.ingestion.subgraph import DimensionedSubgraphSink

from loomground_solver.scenario import Norm, Scenario

OPERATOR_TO_DEONTIC = {"O": "obligatory", "P": "permitted", "F": "prohibited"}
# Versum identifier grammar (subgraph.py:_ID) — sanitize case ids into it.
_ID_BAD = re.compile(r"[^A-Za-z0-9._:/-]")
# The deontic plane's own axis canon (deontic.contract.SOLVER_DIMENSIONS).
DEONTIC_ND = {"facet": "nD",
              "system_id": "system:deontic-solver-dimensions",
              "dimension_count": 5,
              "axes": ["structural", "causal", "intentional", "temporal", "relational"]}


def _ident(raw: str) -> str:
    s = _ID_BAD.sub(".", str(raw)).strip(".")
    return s if s and s[0].isalnum() else "x" + s


def ingest_case_text(case_id: str, text: str, store_root: str) -> dict[str, Any]:
    """Write one case's source text through the honest-write contract."""
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    src_id = "case:" + _ident(case_id)
    sink = DimensionedSubgraphSink(store_root, authorized_store_root=store_root)
    writer = versum_writer(
        sink,
        idempotency_key="panel-e2e:" + _ident(case_id),
        source={"source_id": src_id, "content_digest": digest},
        evidence=[{"evidence_id": src_id + ":source-text",
                   "source_id": src_id,
                   "locator": "source_text",
                   "content_digest": digest}],
        nd=DEONTIC_ND,
    )
    registry = IngesterRegistry()
    registry.register(DeonticIngester())
    return ingest_text(text, registry=registry, writer=writer)


def norm_nodes(store_root: str) -> list[dict[str, Any]]:
    """Persisted norm nodes, envelope re-keying undone (properties + node_id)."""
    out: list[dict[str, Any]] = []
    for sub in load_dimensioned_subgraphs(store_root):
        for node in sub["nodes"]:
            if node.get("node_type") == "norm":
                rec = dict(node.get("properties") or {})
                rec["id"] = node.get("node_id")
                out.append(rec)
    return out


def scenario_from_store(scenario_id: str, store_root: str) -> tuple[Scenario, list[str], list[dict]]:
    """Reconstruct a Scenario from the store. Returns (scenario, gaps, nodes).

    A node that cannot become a solver Norm is a named gap — the signal the
    harness reports, never a silent skip."""
    nodes = norm_nodes(store_root)
    gaps: list[str] = []
    norms: list[Norm] = []
    for n in nodes:
        deo = OPERATOR_TO_DEONTIC.get(str(n.get("operator")))
        act = n.get("action")
        if not deo:
            gaps.append(f"node {n.get('id')}: operator {n.get('operator')!r} has no solver deontic")
            continue
        if not act:
            gaps.append(f"node {n.get('id')}: no action to use as the act")
            continue
        norms.append(Norm(act=str(act), deontic=deo, source=str(n.get("id"))))
    return Scenario(id=scenario_id, norms=norms), gaps, nodes
