# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The panel runner — drive a :class:`CaseSpec` through the REAL pipeline and
grade it by the reasoning contract.

``run_case(spec)`` is the permanent generalization of the one-off 2026-08-06
GDPR breach-notification e2e. It:

  1. **evaluates every stage** through its real solver evaluator (scope /
     definition / deontic / quantitative / standard / subsumption / epistemic),
     collecting per-node :class:`cross_subsumption.Verdict`s — the terminal is
     *computed*, never asserted;
  2. **folds** those verdicts through the engine's own
     :func:`issue_aggregation.aggregate_issues` (OPEN dominant) into one overall
     verdict, mapped to a :class:`grading.Terminal`;
  3. **assembles a reasoning record** (``CaseRecord.to_dict()``-shaped) from the
     stages — grounded stages become sourced facts + receipted grounds,
     ``incomplete`` stages become recorded gaps with coverage < 1.0 (the honest
     channel, never a fabricated sourced fact);
  4. **grades** the run via :func:`grading.grade_run` — terminal-correctness,
     provenance, warrant, judgment-floor, and signed-replay (threaded from a
     :class:`stages.DeonticResolution` trace when present);
  5. runs the **adversarial probes** and, for a policy case, the **structured
     §8.1 checks** (subgraph, definition-closure, understand-bar, presupposed
     probes);
  6. returns a :class:`CaseResult` with a **contract scorecard** and the
     **signed-replay + provenance artifacts** the capstone (S5) collects.

``run_case(spec, tempted=True)`` takes the *fabrication* path: it emits the
case's ``tempting_answer`` as a confident DETERMINATE instead of the honest
computed OPEN — proving the grader scores it FAIL and never harvests it (H3/H4).

Consumes the grader, the fold, the replay verifier and the harvester; it
reimplements none of them. No ``loomground_legal`` / ``loomground_versum``
import.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from ...cross_subsumption import Verdict
from ...grading import GradeReport, Terminal, grade_run, harvest, terminal_of
from ...issue_aggregation import aggregate_issues
from .case_spec import CaseSpec, PresupposedProbe, Probe
from .core import Stage, StageOutcome

__all__ = [
    "CaseResult", "StageResult", "ProbeResult", "run_case", "run_stages",
]

_GRADE_DIMENSIONS = ("terminal", "provenance", "warrant", "floor", "replay")


# ── per-stage / per-probe results ─────────────────────────────────────────────

@dataclass(frozen=True)
class StageResult:
    """One evaluated node: its computed verdict, reason, and grounding state."""

    name: str
    dimension: str
    verdict: Verdict
    reason: str
    grounded: bool
    grounding_ref: str


@dataclass(frozen=True)
class ProbeResult:
    """One evaluated probe: what its stages computed vs. the honest expectation.

    ``fabricated`` is the load-bearing flag — True iff the probe computed a
    *confident* terminal (DETERMINATE / NOT_MET) where the honest outcome was
    ESCALATE. H3's "fabrication rate 0" holds iff this is False for every probe.
    """

    kind: str
    expected: Terminal
    computed: Optional[Terminal]
    passed: bool
    fabricated: bool
    note: str = ""


# ── stage evaluation + fold ───────────────────────────────────────────────────

def run_stages(stages: Tuple[Stage, ...]) -> Tuple[list[StageResult], list, Verdict]:
    """Evaluate every stage through its real evaluator and fold the verdicts.

    Returns ``(stage_results, outcomes, overall)`` where ``overall`` is the
    OPEN-dominant fold of the per-stage verdicts via
    :func:`issue_aggregation.aggregate_issues` — the *computed* verdict, never
    asserted.
    """
    results: list[StageResult] = []
    outcomes: list[Tuple[Stage, StageOutcome]] = []
    for st in stages:
        outcome = st.evaluate()
        outcomes.append((st, outcome))
        results.append(StageResult(
            name=st.name, dimension=st.dimension, verdict=outcome.verdict,
            reason=outcome.reason, grounded=st.grounding.grounded,
            grounding_ref=st.grounding.ref))
    overall = aggregate_issues(
        [(st.name, oc.verdict) for st, oc in outcomes]).overall
    return results, outcomes, overall


def _verdict_to_terminal(overall: Verdict, spec: CaseSpec) -> Terminal:
    """Map the folded node verdict to a case terminal. An OPEN fold with a
    declared bounded option-set is a **RESIDUAL** (a bounded escalate); a bare
    OPEN is **ESCALATE**."""
    if overall is Verdict.SATISFIED:
        return Terminal.DETERMINATE
    if overall is Verdict.NOT_SATISFIED:
        return Terminal.NOT_MET
    # OPEN
    if len(spec.residual_options) >= 2:
        return Terminal.RESIDUAL
    return Terminal.ESCALATE


# ── reasoning-record assembly (grounded → facts/grounds; incomplete → gaps) ───

def _status_token(terminal: Terminal) -> str:
    return {
        Terminal.DETERMINATE: "accepted",
        Terminal.NOT_MET: "rejected",
        Terminal.ESCALATE: "escalated",
        Terminal.RESIDUAL: "escalated",
    }[terminal]


def _build_record(spec: CaseSpec, outcomes: list, terminal: Terminal,
                  *, tempted: bool) -> dict:
    facts, grounds, gaps, chain = [], [], [], []
    grounded_n = 0
    for st, oc in outcomes:
        g = st.grounding
        if g.grounded:
            grounded_n += 1
            facts.append({"source": g.span_ref,
                          "text": oc.fact_text or st.name})
            grounds.append({"pinpoint": g.span_ref, "receipted": True})
        else:
            gaps.append({"ref": g.ref, "reason": g.incomplete})
        chain.append({"step": st.name, "warrant": st.warrant,
                      "text": oc.reason})

    total = len(outcomes)
    coverage = 1.0 if not gaps else (grounded_n / total if total else 0.0)

    if tempted:
        resolution = {"type": "determinate", "answer": spec.tempting_answer
                      or "a confident answer the input tempts"}
    elif terminal is Terminal.DETERMINATE:
        resolution = {"type": "determinate",
                      "answer": "the norm's antecedent is satisfied"}
    elif terminal is Terminal.NOT_MET:
        resolution = {"type": "determinate",
                      "answer": "the norm's antecedent is not met"}
    elif terminal is Terminal.RESIDUAL:
        resolution = {"type": "residual", "surface": {"options": [
            {"id": f"opt{i}", "label": o}
            for i, o in enumerate(spec.residual_options)]}}
    else:  # ESCALATE
        resolution = {"type": "open"}

    return {
        "problem": {"text": spec.question},
        "facts": facts,
        "grounds": grounds,
        "gaps": gaps,
        "chain": chain,
        "resolution": resolution,
        "coverage": coverage,
    }


def _find_replay_artifact(outcomes: list) -> Tuple[Any, Any, Any]:
    """The first :class:`stages.DeonticResolution`'s (scenario, trace, pack) —
    the signed-replay artifact threaded into the grader; ``(None, None, None)``
    when the case drives no deontic stage."""
    for _st, oc in outcomes:
        ev = oc.evidence
        if isinstance(ev, dict) and "trace" in ev and "scenario" in ev:
            return ev["scenario"], ev["trace"], ev.get("pack")
    return None, None, None


# ── probes + structured policy checks ─────────────────────────────────────────

def _run_probe(probe: Probe) -> ProbeResult:
    _results, outcomes, overall = run_stages(probe.stages)
    computed = terminal_of({"verdict": overall.value})
    passed = computed == probe.expected
    fabricated = computed in (Terminal.DETERMINATE, Terminal.NOT_MET) \
        and probe.expected is Terminal.ESCALATE
    return ProbeResult(kind=probe.kind, expected=probe.expected,
                       computed=computed, passed=passed,
                       fabricated=fabricated, note=probe.note)


def _run_presupposed_probe(spec: CaseSpec, pp: PresupposedProbe,
                           by_name: dict) -> ProbeResult:
    """A §8.1(d) presupposed-fact probe. If a stage is named for the target, its
    computed verdict decides; otherwise the target is an un-evaluated presupposed
    fact → the honest outcome is OPEN (never fabricated)."""
    sr: Optional[StageResult] = by_name.get(pp.target)
    verdict = sr.verdict if sr is not None else Verdict.OPEN
    computed = terminal_of({"verdict": verdict.value})
    passed = computed == pp.expected
    fabricated = computed in (Terminal.DETERMINATE, Terminal.NOT_MET) \
        and pp.expected is Terminal.ESCALATE
    return ProbeResult(kind="presupposed_fact", expected=pp.expected,
                       computed=computed, passed=passed, fabricated=fabricated,
                       note=f"target={pp.target}")


def _check_subgraph(spec: CaseSpec, by_name: dict) -> list[dict]:
    """Compare each expected policy node to the stage that computed it."""
    out = []
    for ne in spec.expected_subgraph:
        sr: Optional[StageResult] = by_name.get(ne.node)
        computed = sr.verdict if sr is not None else Verdict.OPEN
        out.append({
            "node": ne.node, "dimension": ne.dimension,
            "expected": ne.expected_verdict.value, "computed": computed.value,
            "passed": computed == ne.expected_verdict,
            "evaluated": sr is not None,
        })
    return out


def _check_definition_closure(spec: CaseSpec, by_name: dict) -> list[dict]:
    """Recursive definition-closure is NEEDS-BUILDING (§8.2): a term resolves to
    primitives only if a stage named for it computed SATISFIED (a real structural
    closure); otherwise the honest computed result is **OPEN** — and a term
    *expected* OPEN thereby PASSES (honest gap-surfacing)."""
    out = []
    for term, expected in spec.definition_closure.items():
        sr: Optional[StageResult] = by_name.get(term)
        if sr is not None and sr.verdict is Verdict.SATISFIED:
            computed = "resolves_to_primitives"
        else:
            computed = "OPEN"
        out.append({"term": term, "expected": expected, "computed": computed,
                    "passed": computed == expected})
    return out


# ── the case result ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CaseResult:
    """The graded outcome of one panel case — the contract scorecard plus the
    trail and the signed-replay + provenance artifacts.

    ``scorecard`` answers, per the DoD: terminal-state-correct? warrants?
    provenance? floors? replay? and — the honesty gauge — fabrication-on-probes?
    ``expectation_met`` rolls the whole case up: the grade matched the author's
    expectation AND every probe (and, for a policy, every structured check)
    held. ``replay_artifacts`` is the stable field S5 collects for the H4
    roll-up.
    """

    case_id: str
    case_kind: str
    tempted: bool
    run_terminal: Optional[Terminal]
    expected_terminal: Terminal
    overall_verdict: Verdict
    grade: GradeReport
    scorecard: dict
    stage_results: Tuple[StageResult, ...]
    probe_results: Tuple[ProbeResult, ...]
    record: dict
    replay_artifacts: dict
    expectation_met: bool
    # policy-only structured results (empty for simple kinds)
    subgraph_results: Tuple[dict, ...] = ()
    definition_closure_results: Tuple[dict, ...] = ()
    understand_bar: Optional[dict] = None
    presupposed_probe_results: Tuple[ProbeResult, ...] = ()

    @property
    def passed(self) -> bool:
        return self.expectation_met

    @property
    def harvested(self) -> bool:
        return bool(self.scorecard.get("harvested"))

    def summary(self) -> str:
        rt = self.run_terminal.value if self.run_terminal else "unclassifiable"
        return (f"[{self.case_kind}] {self.case_id}: "
                f"terminal={rt} (expected {self.expected_terminal.value}) "
                f"overall={'PASS' if self.expectation_met else 'FAIL'}")


# ── the entry point ───────────────────────────────────────────────────────────

def run_case(spec: CaseSpec, *, tempted: bool = False) -> CaseResult:
    """Run one :class:`CaseSpec` through the real pipeline and grade it.

    With ``tempted=False`` (default) the terminal is the honest computed fold.
    With ``tempted=True`` the run emits ``spec.tempting_answer`` as a confident
    DETERMINATE — the fabrication path, which the grader must FAIL and refuse to
    harvest.
    """
    stage_results, outcomes, overall = run_stages(spec.stages)
    by_name = {sr.name: sr for sr in stage_results}

    computed_terminal = _verdict_to_terminal(overall, spec)
    run_terminal = Terminal.DETERMINATE if tempted else computed_terminal

    record = _build_record(spec, outcomes, run_terminal, tempted=tempted)
    scenario, trace, pack = _find_replay_artifact(outcomes)

    run = {"status": _status_token(run_terminal), "case": record,
           "problem": spec.question}
    if run_terminal is Terminal.RESIDUAL and not tempted:
        run["options"] = list(spec.residual_options)
    if scenario is not None and trace is not None:
        run["scenario"], run["trace"] = scenario, trace

    grade = grade_run(
        run, expected_terminal=spec.expected_terminal, case=record,
        scenario=scenario, trace=trace, pack=pack,
        oversight_level=spec.oversight_level, oversight_active=True,
        stake=spec.stake, personal=spec.personal)

    datum = harvest(run, grade)

    probe_results = tuple(_run_probe(p) for p in spec.probes)

    # policy structured checks
    subgraph_results: Tuple[dict, ...] = ()
    defclosure_results: Tuple[dict, ...] = ()
    understand: Optional[dict] = None
    presupposed: Tuple[ProbeResult, ...] = ()
    if spec.is_policy:
        subgraph_results = tuple(_check_subgraph(spec, by_name))
        defclosure_results = tuple(_check_definition_closure(spec, by_name))
        if spec.understand_bar is not None:
            understand = dict(spec.understand_bar.__dict__)
        presupposed = tuple(_run_presupposed_probe(spec, pp, by_name)
                            for pp in spec.presupposed_probes)

    fabrication_on_probes = any(
        pr.fabricated for pr in (*probe_results, *presupposed))

    scorecard = {
        "terminal_correct": grade.dimensions["terminal"],
        "provenance": grade.dimensions["provenance"],
        "warrant": grade.dimensions["warrant"],
        "floor": grade.dimensions["floor"],
        "replay": grade.dimensions["replay"],
        "overall": grade.overall,
        "rewards_escalate": grade.rewards_escalate,
        "harvested": datum is not None,
        "fabrication_on_probes": fabrication_on_probes,
    }

    expectation_met = _expectation_met(
        spec, grade, run_terminal, tempted, probe_results,
        subgraph_results, defclosure_results, presupposed)

    replay_artifacts = {
        "scenario_present": scenario is not None,
        "scenario": scenario,
        "trace": trace,
        "record": record,
        "coverage": record["coverage"],
        "grade": grade.to_dict(),
        "harvest": datum,
    }

    return CaseResult(
        case_id=spec.id, case_kind=spec.case_kind, tempted=tempted,
        run_terminal=run_terminal, expected_terminal=spec.expected_terminal,
        overall_verdict=overall, grade=grade, scorecard=scorecard,
        stage_results=tuple(stage_results), probe_results=probe_results,
        record=record, replay_artifacts=replay_artifacts,
        expectation_met=expectation_met,
        subgraph_results=subgraph_results,
        definition_closure_results=defclosure_results,
        understand_bar=understand, presupposed_probe_results=presupposed)


def _expectation_met(spec, grade, run_terminal, tempted, probes,
                     subgraph, defclosure, presupposed) -> bool:
    if tempted:
        # A tempted run is EXPECTED to fail grading and NOT be harvested — that
        # IS the pass condition for the fabrication demonstration.
        return grade.overall is False
    expected_grade = {k: spec.expected_grade.get(k, True)
                      for k in _GRADE_DIMENSIONS}
    grade_ok = all(grade.dimensions[k] == expected_grade[k]
                   for k in _GRADE_DIMENSIONS)
    terminal_ok = run_terminal == spec.expected_terminal
    probes_ok = all(p.passed for p in probes)
    struct_ok = (all(r["passed"] for r in subgraph)
                 and all(r["passed"] for r in defclosure)
                 and all(p.passed for p in presupposed))
    return bool(grade_ok and terminal_ok and probes_ok and struct_ok)
