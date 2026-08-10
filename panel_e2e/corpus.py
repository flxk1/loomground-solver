# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The deontic e2e corpus — every panel case whose source text the
DeonticIngester can lower, run through the full pipeline with the FROZEN act
identity contract, and scored.

The scorecard's first-class metrics (PO-locked): ``alias_count`` (extraction
coarseness), ``unlowered_count`` (texts the grammar refuses), and
``no_counterpart_count`` (declared normative-level mismatches). ACCEPTANCE
(Option A, accepted 2026-08-10) is stated with the debt visible on purpose:
**4/4 e2e · aliases=0 · unlowered=0 · no_counterpart=3** — "4/4" does NOT
mean zero debt; the three remedy-level hand acts are a counted, deferred
design item, and aliasing them across normative levels would be the exact
meaning-inference this contract rejects.
"""
from __future__ import annotations

import importlib
import json
from typing import Any

from .act_canon import acts_match
from .aliases import ALIASES, NO_COUNTERPART
from .harness import run_case_e2e

CORPUS = (
    "loomground_solver.eval.panel.cases.statutes.gdpr_breach_notification",
    "loomground_solver.eval.panel.cases.statutes.bgb_309_clause_blacklist",
    "loomground_solver.eval.panel.cases.contracts.employment_notice_waiver",
    "loomground_solver.eval.panel.cases.contracts.music_360_perpetual_buyout",
)


def hand_acts(case) -> list[str]:
    out: list[str] = []
    for st in case.stages:
        if type(st).__name__ == "DeonticResolution":
            for norm in getattr(st, "norms", ()):  # (act, modality, source[, ...])
                out.append(str(norm[0]))
    return sorted(set(out))


def run_corpus() -> dict[str, Any]:
    """THE THREE-COLUMN DEBT METRIC (all counted, none conflated):
    alias_count (extraction coarseness) · no_counterpart_count (normative
    level mismatch, declared with reasons) · unlowered_count (texts the
    deontic grammar does not lower at all). Undeclared mismatch = unmatched
    = FAIL."""
    report: dict[str, Any] = {"cases": {}, "alias_count": 0,
                              "no_counterpart_count": 0, "unlowered_count": 0,
                              "unmatched": 0}
    for mod in CORPUS:
        case = importlib.import_module(mod).CASE
        res = run_case_e2e(case)
        e2e = res["lanes"]["e2e"]
        entry: dict[str, Any] = {
            "e2e": e2e.get("status"),
            "level": e2e.get("level"),
            "staged": res["lanes"].get("staged", {}).get("overall"),
            "replay_from_versum": e2e.get("replay_from_versum"),
            "validity_effects": sorted(v.get("effect") or ""
                                       for v in e2e.get("validity_nodes", [])),
            "fallback_stages": res["lanes"].get("staged", {}).get("in_process_fallback_stages", []),
            "acts": [],
        }
        if e2e.get("status") == "UNLOWERED":
            report["unlowered_count"] += 1
            entry["reason"] = e2e.get("reason")
            report["cases"][case.id] = entry
            continue
        # The comparison surface: persisted actions with their RECORDED
        # deadline surface trimmed span-exact (L1(a)); [] at validity level.
        ingested_acts = list(e2e.get("comparable_acts") or [])
        aliases = ALIASES.get(case.id, {})
        no_cp = NO_COUNTERPART.get(case.id, {})
        for hand in hand_acts(case):
            if hand in no_cp:
                entry["acts"].append({"hand": hand, "matched": None,
                                      "level": "no_counterpart",
                                      "reason": no_cp[hand]})
                report["no_counterpart_count"] += 1
                continue
            best = {"matched": False, "level": "none", "detail": {}}
            for ing in ingested_acts:
                m, level, detail = acts_match(hand, ing, aliases=aliases)
                if m:
                    best = {"matched": True, "level": level, "detail": detail}
                    break
                best["detail"] = detail  # keep the last for the failure report
            entry["acts"].append({"hand": hand, **best})
            if best["matched"] and best["level"] == "L2":
                report["alias_count"] += 1
            if not best["matched"]:
                report["unmatched"] += 1
        entry["ingested_acts"] = ingested_acts
        report["cases"][case.id] = entry
    report["verdict"] = ("PASS" if report["unmatched"] == 0 and
                         all(c["e2e"] in ("PASS", "UNLOWERED")
                             for c in report["cases"].values()) else "FAIL")
    return report


if __name__ == "__main__":
    import sys
    rep = run_corpus()
    print(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
    levels = [c.get("level") for c in rep["cases"].values()]
    passed = sum(1 for c in rep["cases"].values() if c["e2e"] == "PASS")
    print(f"CORPUS: {rep['verdict']} — e2e {passed}/{len(rep['cases'])} "
          f"(derivation {levels.count('derivation')}, validity {levels.count('validity')}) · "
          f"aliases={rep['alias_count']} · unlowered={rep['unlowered_count']} · "
          f"unmatched={rep['unmatched']} · "
          f"no_counterpart={rep['no_counterpart_count']} (deferred design debt — counted, not zero)")
    sys.exit(0 if rep["verdict"] == "PASS" else 1)
