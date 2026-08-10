# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""S4 Phase-0 round-trip spike — one deontic case through the REAL planes.

Proves (or names what breaks in) the chain the whole S4 end-to-end DoD rests
on: statute text → loomground-ingest DeonticIngester → Versum store (real
DimensionedSubgraphSink) → load back → reconstruct a solver Scenario from the
PERSISTED norm nodes → derive → the reconstructed trace canonically equals a
hand-authored one, and replay.verify_trace accepts across the boundary.

Deliberately OUTSIDE src/loomground_solver/ (purity invariant: the panel's
case corpus is domain data; this spike touches other planes). Run:

  .venv/bin/python panel_e2e/spike_roundtrip.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from loomground_ingest import DeonticIngester
from loomground_ingest.pipeline import ingest_text
from loomground_ingest.registry import IngesterRegistry
from loomground_ingest.writer import versum_writer
from versum import load_dimensioned_subgraphs
from versum.ingestion.subgraph import DimensionedSubgraphSink

from loomground_solver.eval.panel.cases.statutes.gdpr_breach_notification import CASE
from loomground_solver.replay import verify_trace
from loomground_solver.scenario import Norm, Scenario, derive

OPERATOR_TO_DEONTIC = {"O": "obligatory", "P": "permitted", "F": "prohibited"}


def ingest_into_versum(text: str, store_root: str) -> dict:
    sink = DimensionedSubgraphSink(store_root, authorized_store_root=store_root)
    # The writer fail-closes on empty source/evidence/nd — the honest-write
    # doctrine at the door. Supply what the statute genuinely provides: the
    # source sentence IS the evidence, and the deontic ingester emits its
    # subgraph on the "nD" facet (extraction.json), which nd must match.
    import hashlib
    writer = versum_writer(
        sink,
        idempotency_key="spike:gdpr-art33",
        source={"source_id": "statute:gdpr:art33.1",
                "content_digest": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()},
        evidence=[{"evidence_id": "evidence:gdpr:art33.1:s1",
                   "source_id": "statute:gdpr:art33.1",
                   "locator": "sentence:1",
                   "content_digest": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()}],
        # The nD descriptor comes from the deontic plane's own canon
        # (deontic.contract.SOLVER_DIMENSIONS) — declared, not invented.
        nd={"facet": "nD",
            "system_id": "system:deontic-solver-dimensions",
            "dimension_count": 5,
            "axes": ["structural", "causal", "intentional", "temporal", "relational"]},
    )
    registry = IngesterRegistry()
    registry.register(DeonticIngester())
    return ingest_text(text, registry=registry, writer=writer)


def norm_nodes_from_store(store_root: str) -> list[dict]:
    # Persistence re-keys the ingester's node: kind → node_type, id → node_id,
    # payload fields → properties. Read the envelope's shape, not the raw one.
    out: list[dict] = []
    for sub in load_dimensioned_subgraphs(store_root):
        for node in sub["nodes"]:
            if node.get("node_type") == "norm":
                rec = dict(node.get("properties") or {})
                rec["id"] = node.get("node_id")
                out.append(rec)
    return out


def scenario_from_nodes(nodes: list[dict]) -> tuple[Scenario, list[str]]:
    """Reconstruct a solver Scenario from persisted norm nodes. Anything that
    does not reconstruct is REPORTED, never guessed."""
    gaps: list[str] = []
    norms: list[Norm] = []
    for n in nodes:
        op = n.get("operator")
        deo = OPERATOR_TO_DEONTIC.get(str(op))
        act = n.get("action")
        if not deo:
            gaps.append(f"node {n.get('id')}: operator {op!r} has no solver deontic")
            continue
        if not act:
            gaps.append(f"node {n.get('id')}: no action to use as the act")
            continue
        norms.append(Norm(act=str(act), deontic=deo, source=str(n.get("id"))))
    return Scenario(id="spike.gdpr.art33.reconstructed", norms=norms), gaps


def main() -> int:
    store = tempfile.mkdtemp(prefix="spike_versum_")
    res = ingest_into_versum(CASE.source_text, store)
    print("ingest:", json.dumps({k: res.get(k) for k in ("ok", "ingester", "dimension", "reason")}))
    if not res.get("ok"):
        print("SPIKE: FAIL — ingest refused; nothing to round-trip")
        return 1

    nodes = norm_nodes_from_store(store)
    print(f"store: {len(nodes)} norm node(s) persisted+loaded")
    for n in nodes:
        print("  norm:", json.dumps({k: n.get(k) for k in ("operator", "bearer", "action", "condition", "exception", "deadline")}, ensure_ascii=False))
    if not nodes:
        print("SPIKE: FAIL — no norm nodes persisted (ingest wrote, store returned none)")
        return 1

    reconstructed, gaps = scenario_from_nodes(nodes)
    for g in gaps:
        print("  gap:", g)
    if not reconstructed.norms:
        print("SPIKE: FAIL — nothing reconstructed into solver norms; gaps above are the signal")
        return 1

    # The hand-authored twin: same acts, authored directly from the statute —
    # the acceptance is that PERSISTENCE changed nothing the derivation sees.
    hand = Scenario(
        id="spike.gdpr.art33.hand",
        norms=[Norm(act=n.act, deontic=n.deontic, source=n.source) for n in reconstructed.norms],
    )
    t_hand = derive(hand).trace()
    t_rec = derive(reconstructed).trace()
    # Scenario ids differ by construction; equality is over the DERIVATION.
    t_hand.pop("scenario"), t_rec.pop("scenario")
    if json.dumps(t_hand, sort_keys=True) != json.dumps(t_rec, sort_keys=True):
        print("SPIKE: FAIL — traces diverge:\n hand:", json.dumps(t_hand, sort_keys=True)[:400],
              "\n rec :", json.dumps(t_rec, sort_keys=True)[:400])
        return 1

    # Cross-boundary replay: the solver's own verifier accepts the
    # reconstructed scenario against the hand trace.
    full_hand = derive(hand).trace()
    ok = verify_trace(Scenario(id=full_hand["scenario"], norms=reconstructed.norms), full_hand)
    print("verify_trace(reconstructed vs hand):", ok)
    if not ok:
        print("SPIKE: FAIL — replay verifier rejects the reconstructed scenario")
        return 1

    acts = t_rec.get("acts", {})
    print("derived acts:", json.dumps(acts, ensure_ascii=False)[:300])
    print("SPIKE: PASS — statute text → ingest → versum → reload → solver derive round-trips; "
          f"{len(reconstructed.norms)} norm(s), {len(gaps)} reconstruction gap(s) reported above")
    return 0


if __name__ == "__main__":
    sys.exit(main())
