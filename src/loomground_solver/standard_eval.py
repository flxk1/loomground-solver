# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Standard evaluation (O-STD) — apply an open-textured legal *standard*
("a reasonable person", "good faith", "unconscionable", "undue hardship")
to a set of facts, honestly. An [I]-tier op: the **model fills**, the
**contract gates**, the harness **escalates** where the law hands the call
to a human.

A *rule* has a decidable Tatbestand; a *standard* does not — it is applied
against a **benchmark** (what the reasonable person would have done, what
good faith required here) that a decider must *supply and justify*. That
supply is exactly the step an LLM is tempted to fake: to announce a
confident verdict without naming the benchmark it measured against or the
facts it relied on. This module makes the supply auditable.

The model proposes three things, each **span-tagged and scored**:

  * the **benchmark** the standard sets on these facts (drawn from the facts
    text — the yardstick, not free-floating);
  * the **facts relied on** (the operative facts the application turns on);
  * the **application verdict** (met / not-met), with its confidence.

Then a chain of **deterministic gates** decides whether that proposal may
stand as a verdict at all:

  1. **grounding** (honesty floor) — the benchmark span and every
     relied-on-fact span must be a *substring of the facts text*. A benchmark
     or a fact conjured from nowhere is REJECTED as invented. The harness
     never returns a verdict resting on a fabricated yardstick.
  2. **contestedness** — a standard whose application reasonable people could
     decide either way is *genuinely contested*; the model flags it, and a
     contested application ESCALATES. The harness never converts a contested
     judgement into a confident verdict.
  3. **audit** — the decomposition (relied facts + benchmark ⇒ verdict) is
     verified with :func:`interpret.audit`; a self-contradictory set of
     relied facts, or a verdict the stated grounds do not carry, ESCALATES.
  4. **confidence floor** — NT-9 (:func:`norm_contract.check_confidence` /
     :data:`norm_contract.CONFIDENCE_FLOOR`); sub-floor confidence ESCALATES,
     regardless of any single high self-reported score. Confidence is never
     trusted alone.

Only a proposal that is grounded AND not-contested AND audited AND
at/above the floor is answered — SATISFIED when the benchmark is met,
NOT_SATISFIED when it is not. Everything else escalates or rejects.

It wraps what exists rather than regrowing it: the fill is the injected
:data:`ports.ModelFn`; the reasoning is verified through
:func:`interpret.interpret` (its ``parse`` seam driven by the decoded
proposal) and :func:`interpret.audit`; the floor is the existing
:func:`norm_contract.check_confidence` gate. It reimplements no audit and
no gate.

Pure stdlib (``json``, ``dataclasses``, ``typing``). No governance, no
corpus, no domain: :func:`evaluate_standard` takes a generic standard
``str`` and a facts ``str`` — never a corpus-coupled object, never a real
LLM (the model is injected).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from . import norm_contract
from .interpret import audit as _audit_interp
from .interpret import interpret as _interpret
from .norm_contract import CONFIDENCE_FLOOR, Level
from .ports import ModelFn
from .subsumption import Rule


# ── the proposal schema the ModelFn returns ───────────────────────────────────

@dataclass(frozen=True)
class Element:
    """One span-anchored piece of the application: the ``literal`` the solver
    reasons over, the verbatim ``span`` it was drawn from, and the model's
    ``confidence`` in it."""

    span: str
    literal: str
    confidence: float = 1.0
    role: str = "fact"          # benchmark | fact | verdict

    @classmethod
    def from_dict(cls, d: dict, *, role: str = "fact") -> "Element":
        return cls(span=str(d.get("span", "")),
                   literal=str(d.get("literal", "")),
                   confidence=float(d.get("confidence", 1.0)),
                   role=str(d.get("role", role)))

    def grounded_in(self, text: str) -> bool:
        """Honesty floor: the span must be a substring of the facts text."""
        return bool(self.span) and self.span in text

    def receipt(self, text: str) -> dict[str, Any]:
        """A provenance receipt: where in the facts text this element anchors."""
        start = text.find(self.span) if self.span else -1
        end = start + len(self.span) if start >= 0 else -1
        return {"role": self.role, "literal": self.literal, "span": self.span,
                "start": start, "end": end, "confidence": self.confidence,
                "grounded": start >= 0}


@dataclass(frozen=True)
class StandardProposal:
    """A model's proposed application of a standard. Convention, not truth —
    every field is subject to the gates before it becomes a verdict."""

    benchmark: Optional[Element] = None          # the yardstick the standard sets
    relied_on: tuple[Element, ...] = ()          # the operative facts relied on
    verdict: Optional[Element] = None            # the application conclusion
    met: bool = False                            # benchmark met? (satisfied vs not)
    contested: bool = False                      # reasonable people could differ

    @classmethod
    def from_dict(cls, d: dict) -> "StandardProposal":
        bench = d.get("benchmark")
        verd = d.get("verdict")
        return cls(
            benchmark=(Element.from_dict(bench, role="benchmark")
                       if bench else None),
            relied_on=tuple(Element.from_dict(e, role="fact")
                            for e in (d.get("relied_on") or ())),
            verdict=(Element.from_dict(verd, role="verdict") if verd else None),
            met=bool(d.get("met", False)),
            contested=bool(d.get("contested", False)),
        )

    @classmethod
    def from_json(cls, raw: str) -> "StandardProposal":
        return cls.from_dict(json.loads(raw))

    def grounded_elements(self) -> list[Element]:
        """The elements the grounding gate checks: the benchmark and every
        relied-on fact. The verdict is the model's judgement, not a quotation,
        so it is scored (confidence) but not required to be a substring."""
        out: list[Element] = []
        if self.benchmark is not None:
            out.append(self.benchmark)
        out.extend(self.relied_on)
        return out

    def all_elements(self) -> list[Element]:
        out = self.grounded_elements()
        if self.verdict is not None:
            out.append(self.verdict)
        return out

    def min_confidence(self) -> float:
        confs = [e.confidence for e in self.all_elements()]
        return min(confs) if confs else 0.0


# ── the model port: a deterministic stub for tests ────────────────────────────

class StubModel:
    """A deterministic :data:`ports.ModelFn` (``str -> str``): it ignores the
    prompt and returns a *fixed* canned proposal as JSON. Faithful to the real
    seam — a host's model likewise returns a completion string that
    :func:`evaluate_standard` decodes — but with no model runtime, so the gates
    are exercised deterministically. Construct with the proposal you want::

        model = StubModel({"benchmark": {...}, "relied_on": [...],
                           "verdict": {...}, "met": True})
    """

    def __init__(self, proposal: dict):
        self._payload = json.dumps(proposal)

    def __call__(self, prompt: str) -> str:   # ports.ModelFn
        return self._payload


def _build_prompt(standard: str, facts: str) -> str:
    """The instruction handed to the model. Content is irrelevant to the gates
    (a real model reads it; :class:`StubModel` ignores it) — but the call is a
    genuine ``ModelFn`` invocation, so the seam is consumed, not bypassed."""
    return (
        f"Apply the legal standard {standard!r} to the facts below. Supply the "
        "BENCHMARK the standard sets here (drawn verbatim from the facts as a "
        "SPAN), the FACTS you rely on (each a verbatim SPAN), and your VERDICT "
        "(met true/false) with a confidence. If reasonable people could decide "
        "either way, set contested=true. Reply as JSON.\n\nFACTS:\n" + facts
    )


# ── the result ────────────────────────────────────────────────────────────────

@dataclass
class StandardResult:
    """The outcome of a standard-application attempt. It carries a grounded
    verdict XOR an escalation/rejection — never a confident verdict resting on
    an invented benchmark or a contested call."""

    status: str                                  # satisfied | not_satisfied
    #                                              | rejected | escalated
    verdict: Optional[bool]                      # True=met, False=not-met, None
    benchmark: str                               # the yardstick literal (if any)
    escalated: bool
    reason: str
    gate_report: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def satisfied(self) -> bool:
        return self.status == "satisfied"

    @property
    def not_satisfied(self) -> bool:
        return self.status == "not_satisfied"

    @property
    def rejected(self) -> bool:
        return self.status == "rejected"


def _reject(reason: str, report: dict, prov: dict) -> StandardResult:
    return StandardResult("rejected", None, "", False, reason, report, prov)


def _escalate(reason: str, report: dict, prov: dict,
              benchmark: str = "") -> StandardResult:
    return StandardResult("escalated", None, benchmark, True, reason, report, prov)


# ── the reasoning-audit bridge (consumes interpret.interpret + interpret.audit)─

def _proposal_to_interp(proposal: StandardProposal) -> dict:
    """Cast the application as facts + a rule + a candidate so the existing
    auditor can check it: the relied-on facts (and the benchmark) are taken as
    facts, the benchmark-applied-to-the-facts is a rule
    ``relied + benchmark => verdict``, and the candidate is the verdict. A
    self-contradictory set of relied facts (e.g. ``x`` and ``-x``) then comes
    back inconsistent — the solver catching an incoherent application."""
    bench_lit = proposal.benchmark.literal if proposal.benchmark else ""
    relied = tuple(e.literal for e in proposal.relied_on)
    conds = relied + ((bench_lit,) if bench_lit else ())
    verdict_lit = proposal.verdict.literal if proposal.verdict else ""
    rule = Rule(id="O-STD", conditions=conds, consequence=verdict_lit)
    return {"facts": set(conds), "rules": [rule], "candidate": verdict_lit}


def _audit_reasoning(facts: str, proposal: StandardProposal) -> dict:
    """Fill through :func:`interpret.interpret` (its ``parse`` seam driven by the
    decoded proposal) then verify with :func:`interpret.audit`."""
    interp = _interpret(facts, parse=lambda _t: _proposal_to_interp(proposal))
    return _audit_interp(interp)


# ── the norm-contract bridge (consumes the existing gate function) ────────────

def _nt9_confidence_finding(min_conf: float, risk_class: str):
    """NT-9 via :func:`norm_contract.check_confidence`: sub-floor confidence on
    a class-C context escalates rather than answers."""
    pair = {"id": "O-STD", "solution": {"confidence": min_conf}}
    return norm_contract.check_confidence(pair, risk_class=risk_class)


def _has_escalate(findings) -> bool:
    return any(f.level is Level.ESCALATE for f in findings)


# ── the op ────────────────────────────────────────────────────────────────────

def evaluate_standard(
    standard: str,
    facts: str,
    *,
    model: ModelFn,
    risk_class: str = "C",
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> StandardResult:
    """Apply an open-textured ``standard`` to ``facts``, or escalate/reject.

    The ``model`` (an injected :data:`ports.ModelFn`) proposes a benchmark, the
    facts relied on and a met/not-met verdict; deterministic gates over
    ``(proposal, facts)`` then decide. The gates, in order of precedence:

      * **well-formedness** — a proposal missing the benchmark, the relied-on
        facts or the verdict is malformed → REJECT (no verdict);
      * **grounding** — the benchmark span or any relied-on-fact span not found
        in ``facts`` is invented → REJECT (honesty floor);
      * **contestedness** — a proposal flagged ``contested`` is a call
        reasonable people could decide either way → ESCALATE, never a confident
        verdict;
      * **audit** — :func:`interpret.audit` must find the decomposition sound;
        contradictory relied facts or an unwarranted verdict → ESCALATE;
      * **confidence floor** — NT-9 / :data:`CONFIDENCE_FLOOR`; sub-floor →
        ESCALATE, regardless of any single high self-reported score.

    Only a proposal that is grounded AND not-contested AND audited AND
    at/above the floor is answered: SATISFIED when the benchmark is met,
    NOT_SATISFIED when it is not.

    ``standard`` and ``facts`` are plain strings — the solver is corpus-free
    and never receives a provision or a case object.
    """
    prov: dict[str, Any] = {"standard": standard, "receipts": []}
    report: dict[str, Any] = {}

    # 0. Fill: consume the ModelFn seam and decode the proposal.
    raw = model(_build_prompt(standard, facts))
    try:
        proposal = StandardProposal.from_json(raw) if isinstance(raw, str) \
            else StandardProposal.from_dict(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        report["decode"] = {"ok": False, "error": str(exc)}
        return _reject("model returned an undecodable proposal", report, prov)

    prov["receipts"] = [e.receipt(facts) for e in proposal.all_elements()]
    bench_lit = proposal.benchmark.literal if proposal.benchmark else ""

    # 1. Well-formedness: a verdict needs a benchmark, ≥1 relied fact, a verdict.
    wf_ok = (proposal.benchmark is not None
             and bool(proposal.relied_on)
             and proposal.verdict is not None)
    report["wellformed"] = {
        "ok": wf_ok,
        "reason": "" if wf_ok else "missing benchmark, relied-on facts or verdict",
    }
    if not wf_ok:
        return _reject("malformed proposal: " + report["wellformed"]["reason"],
                       report, prov)

    # 2. Grounding (honesty floor): the benchmark and every relied-on fact must
    #    be a substring of the facts text — reject an invented yardstick/fact.
    invented = [e.span for e in proposal.grounded_elements()
                if not e.grounded_in(facts)]
    report["grounding"] = {"ok": not invented, "invented": invented}
    if invented:
        return _reject(
            f"ungrounded benchmark/fact — span not found in facts: {invented!r}",
            report, prov)

    # 3. Contestedness: a genuinely-contested application is a human's call —
    #    never converted into a confident verdict, whatever the confidence.
    report["contested"] = {"ok": not proposal.contested,
                           "contested": proposal.contested}
    if proposal.contested:
        return _escalate(
            "genuinely contested — reasonable people could decide either way; "
            "human judgement required", report, prov, benchmark=bench_lit)

    # 4. Audit: consume interpret.interpret + interpret.audit. A contradictory
    #    set of relied facts or an unwarranted verdict is unsound → escalate.
    audit_report = _audit_reasoning(facts, proposal)
    audited = audit_report["verdict"] == "sound"
    report["audit"] = {"verdict": audit_report["verdict"],
                       "reasons": audit_report["reasons"]}
    if not audited:
        return _escalate("audit unsound — " + "; ".join(audit_report["reasons"]),
                         report, prov, benchmark=bench_lit)

    # 5. Confidence floor: NT-9 plus a hard floor independent of risk_class.
    #    Confidence is never trusted alone; sub-floor escalates.
    min_conf = proposal.min_confidence()
    nt9 = _nt9_confidence_finding(min_conf, risk_class)
    sub_floor = min_conf < confidence_floor or _has_escalate(nt9)
    report["confidence"] = {"min": min_conf, "floor": confidence_floor,
                            "ok": not sub_floor, "nt9": [f.to_dict() for f in nt9]}
    if sub_floor:
        return _escalate(
            f"sub-floor confidence {min_conf} < {confidence_floor}", report, prov,
            benchmark=bench_lit)

    # 6. Answer — grounded, not-contested, audited, at/above the floor.
    # Belt-and-suspenders: never answer on an ungrounded benchmark/fact.
    assert all(r["grounded"] for r in prov["receipts"]
               if r["role"] in ("benchmark", "fact")), \
        "invariant: answered verdict has an ungrounded benchmark/fact receipt"
    report["answered"] = True
    status = "satisfied" if proposal.met else "not_satisfied"
    reason = ("standard met against a grounded benchmark"
              if proposal.met else
              "standard not met against a grounded benchmark")
    return StandardResult(status, proposal.met, bench_lit, False, reason,
                          report, prov)
