# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Grading — score a harness run against the reasoning contract (deterministic).

A harness (``norm_construction``, ``auslegung``, ``precedent_ratio``,
``structural``/``causal``/``temporal``/``renewal``/``relational`` construction,
or ``cross_subsumption``) emits a *run*: a terminal outcome (accepted / rejected
/ escalated, or SATISFIED / NOT_SATISFIED / OPEN) plus its reasoning record
(provenance, gate report) and — when signed — a replayable trace. This module is
a **pure grader**: given a run, the case's ``expected_terminal`` and the contract
inputs, it returns a :class:`GradeReport`. It is a deterministic function of its
arguments — no model, no LLM, no network.

The grading semantics encode the *inverse-of-accuracy* property. The run is
mapped to a terminal class::

    accepted / extracted / SATISFIED   → DETERMINATE
    rejected / NOT_SATISFIED           → NOT_MET
    escalated / OPEN                   → ESCALATE
    a bounded choice-set               → RESIDUAL

and scored on:

  1. **terminal** — the run's terminal must equal the case's expected terminal.
     A *correct ESCALATE* (expected ESCALATE, run escalated) is a **PASS** —
     escalation on a genuinely open case is success, never a non-answer. A
     *confident fabrication* (expected ESCALATE, run DETERMINATE) is a **FAIL**,
     and so is any confident-wrong DETERMINATE.
  2. **provenance / warrant / floor** — via the contract gates
     (:func:`contract.check_evidence`, :func:`contract.check_warrants`,
     :func:`contract.check_judgment_floor`) over the run's reasoning record. A
     dimension passes iff its gate emits no VIOLATION (an ESCALATE is
     conforming-but-deferred, per the contract).
  3. **signed-replay** — via :func:`replay.verify_trace` over the run's trace,
     when a ``scenario`` + ``trace`` are present; a tampered record fails.

Overall **PASS** iff terminal-correct AND every contract dimension passes.

Only an overall-PASS run is harvested into a training datum (via
:func:`datapump.harvest` / :func:`datapump.to_jsonl`); a FAIL run yields
``None`` — the pump never trains on fabrication.

Pure stdlib. Consumes the existing gates, signer/replay, and harvester — it
reimplements none of them. No ``loomground_legal`` / ``loomground_versum``
dependency: the run and its expected class are generic inputs."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from . import datapump, replay
from .contract import check_evidence, check_judgment_floor, check_warrants
from .norm_contract import Finding, Level


# ── terminal classes ──────────────────────────────────────────────────────────

class Terminal(str, Enum):
    """The four terminal classes a run may resolve to."""

    DETERMINATE = "determinate"   # a grounded, closed answer
    NOT_MET = "not_met"           # the antecedent is not satisfied (closed-world)
    ESCALATE = "escalate"         # open / handed to a human — a correct answer
    RESIDUAL = "residual"         # a bounded, non-empty choice-set


#: harness status/verdict tokens → terminal class.
_TERMINAL_TOKENS: dict[str, Terminal] = {
    "accepted": Terminal.DETERMINATE,
    "extracted": Terminal.DETERMINATE,
    "satisfied": Terminal.DETERMINATE,
    "determinate": Terminal.DETERMINATE,
    "rejected": Terminal.NOT_MET,
    "not_satisfied": Terminal.NOT_MET,
    "not_met": Terminal.NOT_MET,
    "unsatisfied": Terminal.NOT_MET,
    "escalated": Terminal.ESCALATE,
    "escalate": Terminal.ESCALATE,
    "open": Terminal.ESCALATE,
    "residual": Terminal.RESIDUAL,
    "choice": Terminal.RESIDUAL,
    "choice_set": Terminal.RESIDUAL,
}


# ── run accessors (tolerant of dict OR dataclass runs) ─────────────────────────

def _get(run: Any, name: str, default: Any = None) -> Any:
    if isinstance(run, dict):
        return run.get(name, default)
    return getattr(run, name, default)


def _norm_token(value: Any) -> str:
    """The string value of a status/verdict, unwrapping an Enum."""
    return str(getattr(value, "value", value)).strip().lower()


def terminal_of(run: Any) -> Optional[Terminal]:
    """Map a harness run to its terminal class, or ``None`` if unclassifiable.

    Precedence: an explicit ``terminal`` field; a bounded ``options`` /
    ``choice_set`` (≥ 2) → RESIDUAL; a ``verdict`` or ``status`` token; finally a
    truthy ``escalated`` flag."""
    explicit = _get(run, "terminal")
    if explicit is not None:
        return _as_terminal(explicit, strict=False)

    options = _get(run, "options") or _get(run, "choice_set")
    if isinstance(options, (list, tuple)) and len(options) >= 2:
        return Terminal.RESIDUAL

    for key in ("verdict", "status"):
        raw = _get(run, key)
        if raw is not None:
            tok = _norm_token(raw)
            if tok in _TERMINAL_TOKENS:
                return _TERMINAL_TOKENS[tok]

    if _get(run, "escalated"):
        return Terminal.ESCALATE
    return None


def _as_terminal(value: Any, *, strict: bool = True) -> Optional[Terminal]:
    """Coerce a Terminal / name / value / status-token to a :class:`Terminal`."""
    if isinstance(value, Terminal):
        return value
    tok = _norm_token(value)
    for t in Terminal:
        if t.value == tok or t.name.lower() == tok:
            return t
    if tok in _TERMINAL_TOKENS:
        return _TERMINAL_TOKENS[tok]
    if strict:
        raise ValueError(f"unknown terminal class: {value!r}")
    return None


def _run_record(run: Any) -> dict:
    """The run's reasoning record (a ``CaseRecord.to_dict()``-shaped dict) that
    the contract gates score. Looks under ``case`` / ``record`` and falls back to
    a ``provenance`` dict; an empty record trivially satisfies the gates."""
    for key in ("case", "record"):
        rec = _get(run, key)
        if isinstance(rec, dict):
            return rec
    prov = _get(run, "provenance")
    return prov if isinstance(prov, dict) else {}


def _no_violation(findings: list[Finding]) -> bool:
    """A gate dimension passes iff it raised no VIOLATION. ESCALATE findings are
    conforming-but-deferred (contract semantics), not failures."""
    return not any(f.level is Level.VIOLATION for f in findings)


# ── the grade report ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GradeReport:
    """Per-dimension pass/fail plus the overall verdict for one graded run."""

    overall: bool
    run_terminal: Optional[Terminal]
    expected_terminal: Terminal
    dimensions: dict[str, bool] = field(default_factory=dict)
    reason: str = ""
    #: True when the correct answer was to escalate and the run did — escalation
    #: is rewarded as a PASS, never penalised as a non-answer.
    rewards_escalate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "run_terminal": self.run_terminal.value if self.run_terminal else None,
            "expected_terminal": self.expected_terminal.value,
            "dimensions": dict(self.dimensions),
            "reason": self.reason,
            "rewards_escalate": self.rewards_escalate,
        }


# ── the grader ─────────────────────────────────────────────────────────────────

def grade_run(
    run: Any,
    *,
    expected_terminal: Any,
    case: Optional[dict] = None,
    scenario: Any = None,
    trace: Optional[dict] = None,
    pack: Any = None,
    oversight_level: str = "autonomous",
    oversight_active: bool = True,
    stake: bool = False,
    personal: bool = False,
) -> GradeReport:
    """Score ``run`` against the reasoning contract.

    :param run: a harness run (dict or dataclass) carrying a terminal
        status/verdict, optionally its reasoning record (``case``) and a signed
        ``scenario`` + ``trace``.
    :param expected_terminal: the case's expected terminal class (a
        :class:`Terminal`, its name/value, or a harness status token).
    :param case: the run's reasoning record for the contract gates; defaults to
        the run's own ``case`` / ``record`` / ``provenance``.
    :param scenario, trace, pack: inputs for the signed-replay check; the replay
        dimension is scored only when both ``scenario`` and ``trace`` are present.
    :param oversight_level, oversight_active, stake, personal: the judgment-floor
        parameters forwarded to :func:`contract.check_judgment_floor`.
    """
    expected = _as_terminal(expected_terminal)
    record = case if case is not None else _run_record(run)
    scenario = scenario if scenario is not None else _get(run, "scenario")
    trace = trace if trace is not None else _get(run, "trace")

    run_terminal = terminal_of(run)

    # 1. terminal correctness — a correct ESCALATE passes; a confident
    #    fabrication (expected ESCALATE, run DETERMINATE) fails.
    terminal_ok = run_terminal is not None and run_terminal == expected
    rewards_escalate = (
        expected is Terminal.ESCALATE and run_terminal is Terminal.ESCALATE
    )

    # 2. contract dimensions — consume the gates; a dimension passes iff no
    #    VIOLATION (an ESCALATE finding is conforming-but-deferred).
    provenance_ok = _no_violation(check_evidence(record))
    warrant_ok = _no_violation(check_warrants(record))
    floor_ok = _no_violation(check_judgment_floor(
        record,
        oversight_level=oversight_level,
        oversight_active=oversight_active,
        stake=stake,
        personal=personal,
    ))

    # 3. signed-replay — re-derive from inputs and confirm the trace is
    #    unaltered; only scored when a signed trace is present.
    if scenario is not None and trace is not None:
        replay_ok = bool(replay.verify_trace(scenario, trace, pack=pack))
    else:
        replay_ok = True  # not applicable — no signed trace on this run

    dimensions = {
        "terminal": terminal_ok,
        "provenance": provenance_ok,
        "warrant": warrant_ok,
        "floor": floor_ok,
        "replay": replay_ok,
    }
    overall = all(dimensions.values())

    reason = _reason(run_terminal, expected, dimensions, rewards_escalate)
    return GradeReport(
        overall=overall,
        run_terminal=run_terminal,
        expected_terminal=expected,
        dimensions=dimensions,
        reason=reason,
        rewards_escalate=rewards_escalate,
    )


def _reason(run_terminal: Optional[Terminal], expected: Terminal,
            dims: dict[str, bool], rewards_escalate: bool) -> str:
    if not dims["terminal"]:
        got = run_terminal.value if run_terminal else "unclassifiable"
        if expected is Terminal.ESCALATE and run_terminal is Terminal.DETERMINATE:
            return ("confident fabrication: the case is open (expected ESCALATE) "
                    "but the run returned a DETERMINATE answer")
        return f"terminal mismatch: expected {expected.value}, got {got}"
    failed = [k for k, ok in dims.items() if not ok and k != "terminal"]
    if failed:
        return "contract dimensions failed: " + ", ".join(sorted(failed))
    if rewards_escalate:
        return "correct escalation on an open case — PASS"
    return "grounded and terminal-correct — PASS"


# ── harvest: a PASS run becomes a training datum (never a FAIL run) ─────────────

def harvest(
    run: Any,
    grade: GradeReport,
    *,
    problem: Optional[str] = None,
    candidate: Optional[str] = None,
    rationale: Optional[str] = None,
) -> Optional[dict]:
    """Harvest an overall-PASS run into a training datum via
    :func:`datapump.harvest` / :func:`datapump.to_jsonl`; a FAIL run returns
    ``None`` so the verifier data-pump never trains on fabrication.

    Returns ``{"record", "examples", "jsonl", "stats"}`` for a PASS run — the
    verified-run record, the SFT examples the pump derived from it, and the
    JSONL rendering."""
    if not grade.overall:
        return None

    record = _run_record(run)
    prob = problem if problem is not None else (
        _get(run, "problem")
        or str((record.get("problem") or {}).get("text", ""))
    )
    cand = candidate if candidate is not None else (
        _get(run, "candidate")
        or str((record.get("resolution") or {}).get("answer", ""))
        or grade.run_terminal.value if grade.run_terminal else ""
    )
    why = rationale if rationale is not None else (
        _get(run, "rationale") or grade.reason
    )

    verified_run = {
        "problem": prob,
        "candidate": cand,
        "passed": True,               # only a PASS run reaches here
        "signature": _get(run, "signature"),
        "rationale": why,
        "trace": _get(run, "trace"),
    }
    bundle = datapump.harvest([verified_run])
    jsonl = datapump.to_jsonl(bundle)
    return {
        "record": verified_run,
        "examples": bundle["examples"],
        "jsonl": jsonl,
        "stats": bundle["stats"],
    }
