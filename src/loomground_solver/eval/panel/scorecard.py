# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""S5 — the DoD scorecard: roll the whole panel up against the "hit high" bars.

Runs every discovered case through :func:`runner.run_case` (honest *and* tempted)
and aggregates the per-case contract scorecards into the Definition-of-Done
report, mapped onto the five acceptance bars H1–H5 from the plan:

  * **H1 · [D] core**      — every case reaches its *correct* terminal state
    (``terminal_correct`` + ``expectation_met``); a computed state, never asserted.
  * **H2 · [I] gating**    — every interpretive step is sourced (``provenance``)
    and warranted (``warrant``); no ungrounded reading passes.
  * **H3 · [E] honesty**   — the load-bearing one: **fabrication rate 0** under the
    adversarial probes, and every temptation case *fails* the grade when tempted
    (confident fabrication → FAIL, not harvested).
  * **H4 · contract-graded** — ``grade.overall`` holds, signed-replay verifies where
    a deontic resolution is present, PASS-only harvesting into datapump.
  * **H5 · policy (§8.1)**  — policy cases lower to a span-grounded-or-honestly-
    incomplete 5D+nD subgraph; nodes and definition-closure grade correctly
    (OPEN is a first-class pass).

This module GRADES; it does not re-implement grading — it consumes the
``CaseResult`` scorecards `runner.run_case` already produces (which consume
`solver.grading`). "Done is not answers-everything": a correct ESCALATE/RESIDUAL
is a pass, so the bar is *correct-state + honesty*, not answer coverage.
"""
from __future__ import annotations

from dataclasses import dataclass

from .registry import collect_cases
from .runner import CaseResult, run_case


@dataclass
class BarResult:
    """One acceptance bar's roll-up."""
    bar: str
    passed: int
    total: int
    failures: tuple = ()

    @property
    def clean(self) -> bool:
        return not self.failures and self.passed == self.total

    def line(self) -> str:
        mark = "PASS" if self.clean else "FAIL"
        extra = "" if self.clean else f" — {list(self.failures)}"
        return f"[{mark}] {self.bar}: {self.passed}/{self.total}{extra}"


@dataclass
class DodScorecard:
    """The panel-wide DoD roll-up."""
    n_cases: int
    by_kind: dict
    terminal_distribution: dict
    bars: dict                       # H1..H5 -> BarResult
    fabrication_rate: float
    replay_sources: int
    harvested: int
    hit_high: bool
    notes: tuple = ()

    def render(self) -> str:
        out = ["=" * 68, "DoD SCORECARD — the graded panel (statutes · contracts · policies)",
               "=" * 68,
               f"cases: {self.n_cases}   by kind: {self.by_kind}",
               f"terminal distribution: {self.terminal_distribution}",
               f"signed-replay sources (H4): {self.replay_sources}   harvested (PASS-only): {self.harvested}",
               f"fabrication rate under adversarial probes: {self.fabrication_rate:.0%}",
               "-" * 68]
        for h in ("H1", "H2", "H3", "H4", "H5"):
            out.append(self.bars[h].line())
        out.append("-" * 68)
        for n in self.notes:
            out.append(f"note: {n}")
        out.append("=" * 68)
        out.append(f"HIT HIGH: {'YES' if self.hit_high else 'NO'}")
        out.append("=" * 68)
        return "\n".join(out)


def run_panel(cases=None) -> list[CaseResult]:
    """Run every discovered case honestly (non-tempted)."""
    specs = cases if cases is not None else collect_cases()
    return [run_case(s) for s in specs]


def dod_scorecard(cases=None) -> DodScorecard:
    """Grade the whole panel against H1–H5. Consumes each case's contract
    scorecard; a case with a ``tempting_answer`` is additionally run *tempted* to
    prove confident fabrication FAILS (H3/H4)."""
    specs = list(cases if cases is not None else collect_cases())
    results = [run_case(s) for s in specs]

    by_kind: dict = {}
    terminal_dist: dict = {}
    for r in results:
        by_kind[r.case_kind] = by_kind.get(r.case_kind, 0) + 1
        key = r.expected_terminal.value
        terminal_dist[key] = terminal_dist.get(key, 0) + 1

    # ── H1: correct terminal, computed not asserted ──────────────────────────
    h1_fail = tuple(r.case_id for r in results
                    if not (r.scorecard["terminal_correct"] and r.expectation_met))
    h1 = BarResult("H1 [D] correct terminal state", len(results) - len(h1_fail),
                   len(results), h1_fail)

    # ── H2: sourced + warranted (no ungrounded reading passes) ───────────────
    h2_fail = tuple(r.case_id for r in results
                    if not (r.scorecard["provenance"] and r.scorecard["warrant"]))
    h2 = BarResult("H2 [I] sourced + warranted", len(results) - len(h2_fail),
                   len(results), h2_fail)

    # ── H3: honesty under load — fabrication rate 0, escalate rewarded ───────
    from .core import Terminal
    fabricators = set(r.case_id for r in results
                      if r.scorecard["fabrication_on_probes"])
    # an ESCALATE case must be *rewarded* as a correct escalation (harvestable).
    # RESIDUAL is a different, bounded pass — rewards_escalate is ESCALATE-specific,
    # so it is NOT required of RESIDUAL cases.
    esc_fail = set(r.case_id for r in results
                   if r.expected_terminal is Terminal.ESCALATE
                   and not r.scorecard["rewards_escalate"])
    # tempted-fabrication proof: any case with a tempting answer, run TEMPTED, must
    # be CAUGHT — for a tempted run ``expectation_met is True`` IS the pass (it means
    # the confident fabrication correctly failed the grade) and it must not harvest.
    tempt_fail = set()
    for s in specs:
        if getattr(s, "tempting_answer", ""):
            tr = run_case(s, tempted=True)
            caught = tr.expectation_met and not tr.harvested
            if not caught:
                tempt_fail.add(s.id)
    h3_fail = tuple(sorted(fabricators | esc_fail | tempt_fail))
    h3 = BarResult("H3 [E] honesty (fabrication rate 0)",
                   len(results) - len(h3_fail), len(results), h3_fail)

    # ── H4: contract-graded — overall + replay + PASS-only harvest ───────────
    h4_fail = tuple(r.case_id for r in results
                    if not (r.scorecard["overall"] and r.scorecard["replay"]))
    h4 = BarResult("H4 contract-graded (overall + replay)",
                   len(results) - len(h4_fail), len(results), h4_fail)
    replay_sources = sum(1 for r in results
                         if r.replay_artifacts.get("scenario_present"))
    harvested = sum(1 for r in results if r.scorecard["harvested"])

    # ── H5: policy 5D+nD (only over policy cases; OPEN is a pass) ─────────────
    policy = [r for r in results if r.case_kind == "policy"]
    h5_fail = []
    for r in policy:
        node_ok = all(nr.get("passed", False) for nr in r.subgraph_results)
        def_ok = all(dr.get("passed", False) for dr in r.definition_closure_results)
        if not (node_ok and def_ok and r.expectation_met):
            h5_fail.append(r.case_id)
    h5 = BarResult("H5 policy 5D+nD subgraph", len(policy) - len(h5_fail),
                   len(policy), tuple(h5_fail))

    fabrication_rate = len(fabricators) / len(results) if results else 0.0
    bars = {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5}

    notes = []
    if not policy:
        notes.append("H5 pending — 0 policy cases yet (S3 in flight); statute+contract "
                     "buckets complete.")
    hit_high = all(b.clean for b in (h1, h2, h3, h4)) and (h5.clean or not policy)

    return DodScorecard(
        n_cases=len(results), by_kind=by_kind, terminal_distribution=terminal_dist,
        bars=bars, fabrication_rate=fabrication_rate, replay_sources=replay_sources,
        harvested=harvested, hit_high=hit_high, notes=tuple(notes))


def main() -> None:  # pragma: no cover - CLI convenience
    print(dod_scorecard().render())


if __name__ == "__main__":  # pragma: no cover
    main()
