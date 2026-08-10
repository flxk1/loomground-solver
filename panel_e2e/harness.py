# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""run_case_e2e — one panel case through the real pipeline, honestly split.

For a deontic case: ingest its ``source_text`` through the planes, reconstruct
the Scenario FROM THE STORE, derive, capture (record + trace + norms) into the
case's Versum store via the runtime capture door, then REPLAY FROM VERSUM —
reload the captured trace and verify it against a freshly reconstructed
scenario. Everything that reaches a verdict via persisted state is labelled
``e2e``; the case's staged run (the panel's own contract grading) is executed
by the EXISTING in-process runner and labelled ``in_process_fallback`` wherever
its stages rest on constructions the DeonticIngester does not lower yet.
An honest gap is a labelled gap — never a fake.
"""
from __future__ import annotations

import json
import tempfile
from typing import Any

from versum.capture import append_record
from versum.store.retrieve import iter_records

from loomground_solver.eval.panel.runner import run_case
from loomground_solver.replay import verify_trace
from loomground_solver.scenario import Scenario, derive

from .bridge import (comparable_acts, ingest_case_text, scenario_from_store,
                     validity_nodes)

# Stage kinds the DeonticIngester lowers today: only the deontic resolution
# itself. Every other construction is an honest in-process fallback and a
# backlog item for Lane A.
E2E_LOWERABLE_STAGES = {"DeonticResolution"}


def _staged_lane(case) -> dict[str, Any]:
    """The panel's own in-process grading — attached to EVERY result so an
    UNLOWERED/FAIL e2e lane still shows whether the case itself is healthy
    (the evidence behind 'coverage absence, not breakage')."""
    staged = run_case(case)
    fallback = sorted({type(s).__name__ for s in case.stages
                       if type(s).__name__ not in E2E_LOWERABLE_STAGES})
    return {
        "terminal": str(getattr(staged, "run_terminal", "")),
        "expected": str(getattr(staged, "expected_terminal", "")),
        "overall": str(getattr(staged, "overall_verdict", "")),
        "mode": "in_process_fallback" if fallback else "e2e-lowerable",
        "in_process_fallback_stages": fallback,
        "note": ("stages not lowered by DeonticIngester yet — run in-process, "
                 "labelled, never faked as reconstructed" if fallback else ""),
    }


def run_case_e2e(case) -> dict[str, Any]:
    result: dict[str, Any] = {"case": case.id, "lanes": {}}
    store = tempfile.mkdtemp(prefix="panel_e2e_")
    result["store"] = store
    # Staged lane first: independent of the store, and every early return
    # below must still carry it.
    result["lanes"]["staged"] = _staged_lane(case)

    # ── e2e lane: text → planes → store → scenario → derive ────────────
    ing = ingest_case_text(case.id, case.source_text, store)
    lane: dict[str, Any] = {"ingest_ok": bool(ing.get("ok")),
                            "ingester": ing.get("ingester")}
    if not ing.get("ok"):
        if ing.get("reason") == "no_ingester":
            # The deontic grammar did not CLAIM the text at dispatch (no
            # modal cues — e.g. void-clause prose). The plane's own honest
            # refusal; coverage absence, not breakage.
            lane["status"] = "UNLOWERED"
            lane["reason"] = "deontic grammar does not claim this text (no_ingester) — a coverage gap, not a failure"
        else:
            lane["status"] = "FAIL"
            lane["reason"] = ing.get("reason")
        result["lanes"]["e2e"] = lane
        return result
    scenario, gaps, nodes = scenario_from_store("e2e:" + case.id, store)
    vnodes = validity_nodes(store)
    lane["norm_nodes"] = len(nodes)
    lane["validity_nodes"] = [{"effect": v.get("effect"),
                               "incident": v.get("incident"),
                               "correlative": v.get("correlative")}
                              for v in vnodes]
    lane["reconstruction_gaps"] = gaps
    if not nodes:
        if vnodes:
            # No conduct norms, but CONSTITUTIVE validity norms persisted
            # and reloaded from the store: the text lowers at the VALIDITY
            # level (void-clause prose). Nothing to derive or replay — the
            # e2e claim is persistence + reconstruction, honestly labelled.
            lane["level"] = "validity"
            lane["status"] = "PASS"
            lane["comparable_acts"] = []
            result["lanes"]["e2e"] = lane
            return result
        # Ingest succeeded but extracted no norms: the text does not lower
        # under the deontic grammar (e.g. prose with neither an O/P/F modal
        # nor a validity cue). Coverage ABSENCE, honestly distinct from
        # breakage.
        lane["status"] = "UNLOWERED"
        lane["reason"] = "text carries no norms the deontic grammar lowers — a coverage gap, not a failure"
        result["lanes"]["e2e"] = lane
        return result
    lane["level"] = "derivation"
    lane["comparable_acts"] = comparable_acts(nodes)
    if not scenario.norms:
        lane["status"] = "FAIL"
        lane["reason"] = "norm nodes persisted but none reconstructed — gaps are the signal"
        result["lanes"]["e2e"] = lane
        return result
    outcome = derive(scenario)
    trace = outcome.trace()
    lane["acts"] = {a: {"status": r.status, "verdict": r.verdict}
                    for a, r in outcome.acts.items()}

    # Capture: the derivation is RECORDED into the same store (runtime door).
    receipt = append_record(
        store,
        record={"kind": "panel-e2e-derivation", "case": case.id,
                "trace": trace,
                "norms": [n.to_dict() for n in scenario.norms]},
        dimension="provenance",
        actor="panel-e2e",
    )
    lane["capture"] = getattr(receipt, "idempotency_key", None) or "recorded"

    # Replay FROM VERSUM: reload the captured trace, reconstruct the scenario
    # AGAIN from the store, and let the solver's own verifier judge.
    reloaded_trace = None
    for node in iter_records(store):
        rec = (node.get("properties") or {}).get("record") if isinstance(node, dict) else None
        if isinstance(rec, dict) and rec.get("kind") == "panel-e2e-derivation" and rec.get("case") == case.id:
            reloaded_trace = rec.get("trace")
            break
    if reloaded_trace is None:
        lane["status"] = "FAIL"
        lane["reason"] = "captured derivation did not come back from the store"
        result["lanes"]["e2e"] = lane
        return result
    fresh, _, _ = scenario_from_store(trace["scenario"], store)
    replay_ok = verify_trace(Scenario(id=str(reloaded_trace.get("scenario")), norms=fresh.norms),
                             reloaded_trace)
    lane["replay_from_versum"] = bool(replay_ok)
    lane["status"] = "PASS" if replay_ok else "FAIL"
    result["lanes"]["e2e"] = lane
    return result


def main(case_module: str = "loomground_solver.eval.panel.cases.statutes.gdpr_breach_notification") -> int:
    import importlib
    case = importlib.import_module(case_module).CASE
    res = run_case_e2e(case)
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str)[:2000])
    e2e = res["lanes"].get("e2e", {})
    status = e2e.get("status")
    # Tri-state, same semantics as the corpus verdict: UNLOWERED is a named
    # coverage gap, not a failure — exit 0, print the true state.
    print("HARNESS:", status)
    return 0 if status in ("PASS", "UNLOWERED") else 1


if __name__ == "__main__":
    import sys
    sys.exit(main(*sys.argv[1:]))
