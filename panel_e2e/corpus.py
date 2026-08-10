# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The deontic e2e corpus — every panel case whose source text the
DeonticIngester can lower, run through the full pipeline with the FROZEN act
identity contract, and scored.

The scorecard's first-class metric (PO-locked): ``alias_count`` — the number
of L2 human-declared act equivalences the corpus needs today. That number IS
the extraction-coarseness debt; Lane A's go/no-go reads it directly.
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
            "staged": res["lanes"].get("staged", {}).get("overall"),
            "replay_from_versum": e2e.get("replay_from_versum"),
            "fallback_stages": res["lanes"].get("staged", {}).get("in_process_fallback_stages", []),
            "acts": [],
        }
        if e2e.get("status") == "UNLOWERED":
            report["unlowered_count"] += 1
            entry["reason"] = e2e.get("reason")
            report["cases"][case.id] = entry
            continue
        ingested_acts = sorted((e2e.get("acts") or {}).keys())
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
    print(f"CORPUS: {rep['verdict']} — aliases={rep['alias_count']} · no_counterpart={rep['no_counterpart_count']} · unlowered={rep['unlowered_count']} (the Lane A numbers), "
          f"unmatched={rep['unmatched']}")
    sys.exit(0 if rep["verdict"] == "PASS" else 1)
