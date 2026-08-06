# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Norm construction (O26) — Normtext → a *grounded* :class:`subsumption.Rule`,
or an honest ESCALATE. An [I]-tier op: the **model fills**, the **contract
gates**, the harness **escalates** where it cannot ground.

The universal solver already knows how to *reason with* a rule (subsume → apply
→ resolve). What it lacked is a trustworthy way to *build* one from prose without
inventing law. This module supplies that door, and it is deliberately not a
decider: a model proposes a decomposition of a norm-text (its Tatbestand,
Rechtsfolge, Ausnahmen and modality), each element **tagged with the source span
it was drawn from** and a confidence, and then a chain of **deterministic gates**
decides whether that proposal may become a Rule at all.

It wraps what exists rather than regrowing it:

  * the fill is the injected :data:`ports.ModelFn` (``str -> str``): the package
    never binds a model; the completion is a JSON proposal it decodes;
  * the reasoning is verified through :func:`interpret.interpret` (the fill seam,
    driven here by the decoded proposal) and :func:`interpret.audit` (the
    solver catching an unwarranted leap or a self-contradictory decomposition);
  * the norm-theoretic floor is the existing contract: NT-5 exception faithful-
    ness (:func:`norm_contract.check_exception`), NT-9 confidence
    (:func:`norm_contract.check_confidence` / :data:`norm_contract.CONFIDENCE_FLOOR`)
    and NT-4 discretion (:func:`norm_contract.check_deontic`);
  * the output shape is a plain :class:`subsumption.Rule`.

The honesty floor is committed, not optional:

  1. **grounding** — every proposed span must be a *substring of the input text*.
     An element whose span is not found is REJECTED as invented. The harness
     never returns an ungrounded Rule.
  2. **faithfulness = span-coverage** — the claimed spans must cover the
     operative content of the text; a dropped operative clause (notably an
     absorbed exception) is FLAGGED and the construction escalates.
  3. **confidence is never trusted alone** — a high self-reported score cannot
     buy an acceptance past thin grounding or an unsound audit. Acceptance
     requires *grounded AND faithful AND audited AND at/above the floor*.

Pure stdlib (``json``, ``re``, ``dataclasses``, ``typing``). No governance, no
corpus, no domain: ``construct_norm`` takes a generic norm-text ``str`` and an
optional ``locus`` pinpoint ``str`` — never a corpus-coupled provision object.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from . import norm_contract
from .interpret import audit as _audit_interp
from .interpret import interpret as _interpret
from .norm_contract import CONFIDENCE_FLOOR, Level
from .ports import ModelFn
from .subsumption import Rule


# ── operative-content tokenisation (for the span-coverage gate) ───────────────
# Faithfulness is span-coverage: every *operative* word of the text must live
# inside some claimed span. Only pure structural glue is discounted — modal and
# conditional words (shall/must/may/not/unless/where/if) stay operative, because
# dropping them changes the norm.

_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÿ]+")
_FRAMING_WORDS = frozenset({
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "that",
    "this", "by", "as", "with", "from", "is", "are", "be", "its", "their",
    "it", "but", "while", "also",
})


def _content_tokens(text: str) -> set[str]:
    """The operative content words of ``text`` (lower-cased, framing removed)."""
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _FRAMING_WORDS}


# ── the proposal schema the ModelFn returns ───────────────────────────────────

@dataclass(frozen=True)
class Element:
    """One decomposed piece of the norm: a literal the solver reasons over, the
    verbatim ``span`` it was drawn from, and the model's confidence in it."""

    span: str
    literal: str
    confidence: float = 1.0
    role: str = "condition"     # condition | consequence | exception

    @classmethod
    def from_dict(cls, d: dict, *, role: str = "condition") -> "Element":
        return cls(span=str(d.get("span", "")),
                   literal=str(d.get("literal", "")),
                   confidence=float(d.get("confidence", 1.0)),
                   role=str(d.get("role", role)))

    def grounded_in(self, text: str) -> bool:
        """Honesty floor #1: the span must be a substring of the input text."""
        return bool(self.span) and self.span in text

    def receipt(self, text: str) -> dict[str, Any]:
        """A provenance receipt: where in the text this element is anchored."""
        start = text.find(self.span) if self.span else -1
        end = start + len(self.span) if start >= 0 else -1
        return {"role": self.role, "literal": self.literal, "span": self.span,
                "start": start, "end": end, "confidence": self.confidence,
                "grounded": start >= 0}


@dataclass(frozen=True)
class NormProposal:
    """A model's proposed decomposition of a norm-text. Convention, not truth —
    every field is subject to the gates before any of it becomes a Rule."""

    elements: tuple[Element, ...] = ()          # the Tatbestand (conditions)
    consequence: Optional[Element] = None       # the Rechtsfolge
    exceptions: tuple[Element, ...] = ()         # the Ausnahmen
    modality: str = ""                           # obligatory|permitted|prohibited|''
    act: str = ""
    modal_phrase: str = ""                       # the surface phrasing (kann/soll/may…)

    @classmethod
    def from_dict(cls, d: dict) -> "NormProposal":
        cons = d.get("consequence")
        return cls(
            elements=tuple(Element.from_dict(e, role="condition")
                           for e in (d.get("elements") or ())),
            consequence=(Element.from_dict(cons, role="consequence")
                         if cons else None),
            exceptions=tuple(Element.from_dict(e, role="exception")
                             for e in (d.get("exceptions") or ())),
            modality=str(d.get("modality", "")),
            act=str(d.get("act", "")),
            modal_phrase=str(d.get("modal_phrase", "")),
        )

    @classmethod
    def from_json(cls, raw: str) -> "NormProposal":
        return cls.from_dict(json.loads(raw))

    def all_elements(self) -> list[Element]:
        out = list(self.elements)
        if self.consequence is not None:
            out.append(self.consequence)
        out.extend(self.exceptions)
        return out

    def min_confidence(self) -> float:
        confs = [e.confidence for e in self.all_elements()]
        return min(confs) if confs else 0.0


# ── the model port: a deterministic stub for tests ────────────────────────────

class StubModel:
    """A deterministic :data:`ports.ModelFn` (``str -> str``): it ignores the
    prompt and returns a *fixed* canned proposal as JSON. Faithful to the real
    seam — a host's model likewise returns a completion string that
    :func:`construct_norm` decodes — but with no model runtime, so the gates are
    exercised deterministically. Construct with the proposal you want proposed::

        model = StubModel({"elements": [...], "consequence": {...}, ...})
    """

    def __init__(self, proposal: dict):
        self._payload = json.dumps(proposal)

    def __call__(self, prompt: str) -> str:   # ports.ModelFn
        return self._payload


def _build_prompt(text: str, locus: str) -> str:
    """The instruction handed to the model. Content is irrelevant to the gates
    (a real model reads it; :class:`StubModel` ignores it) — but the call is a
    genuine ``ModelFn`` invocation, so the seam is consumed, not bypassed."""
    head = f"Decompose the following norm-text{f' ({locus})' if locus else ''} "
    return (head + "into grounded elements. For each condition, the consequence "
            "and each exception, return the verbatim source SPAN, a solver "
            "literal and a confidence. Reply as JSON.\n\n" + text)


# ── the result ────────────────────────────────────────────────────────────────

@dataclass
class ConstructionResult:
    """The outcome of a construction attempt. It carries a grounded Rule XOR an
    escalation/rejection — never an ungrounded Rule."""

    status: str                                  # accepted | rejected | escalated
    rule: Optional[Rule]
    escalated: bool
    reason: str
    gate_report: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"

    @property
    def rejected(self) -> bool:
        return self.status == "rejected"


def _reject(reason: str, report: dict, prov: dict) -> ConstructionResult:
    return ConstructionResult("rejected", None, False, reason, report, prov)


def _escalate(reason: str, report: dict, prov: dict) -> ConstructionResult:
    return ConstructionResult("escalated", None, True, reason, report, prov)


# ── the reasoning-audit bridge (consumes interpret.interpret + interpret.audit)─

def _proposal_to_interp(proposal: NormProposal) -> dict:
    """Cast the decomposition as facts + a rule + a candidate so the existing
    auditor can check it: the conditions are taken as facts, the rule is
    ``conditions => consequence``, and the candidate is the consequence. A
    self-contradictory Tatbestand (e.g. ``x`` and ``-x``) then comes back
    inconsistent; a consequence the conditions cannot reach comes back
    unwarranted — the solver catching an incoherent decomposition."""
    conds = tuple(e.literal for e in proposal.elements)
    cons = proposal.consequence.literal if proposal.consequence else None
    rule = Rule(id="O26", conditions=conds, consequence=cons or "",
                exceptions=tuple(e.literal for e in proposal.exceptions))
    return {"facts": set(conds), "rules": [rule], "candidate": cons}


def _audit_reasoning(text: str, proposal: NormProposal) -> dict:
    """Fill through :func:`interpret.interpret` (its ``parse`` seam driven by the
    decoded proposal) then verify with :func:`interpret.audit`."""
    interp = _interpret(text, parse=lambda _t: _proposal_to_interp(proposal))
    return _audit_interp(interp)


# ── the norm-contract bridges (consume the existing gate functions) ───────────

def _nt5_exception_finding(text: str, proposal: NormProposal):
    """NT-5 via :func:`norm_contract.check_exception`: exception phrasing in the
    body that the proposal did not flag is an absorbed exception."""
    pair = {"id": "O26",
            "problem": {"facets": {"has_exception": bool(proposal.exceptions)}},
            "solution": {"body": text}}
    return norm_contract.check_exception(pair)


def _nt9_confidence_finding(min_conf: float, risk_class: str):
    """NT-9 via :func:`norm_contract.check_confidence`."""
    pair = {"id": "O26", "solution": {"confidence": min_conf}}
    return norm_contract.check_confidence(pair, risk_class=risk_class)


def _nt4_deontic_finding(proposal: NormProposal):
    """NT-4 via :func:`norm_contract.check_deontic`: a discretionary modality
    (kann/soll/may…) is the law handing the call to a human — it escalates."""
    pair = {"id": "O26",
            "problem": {"type": "rule",
                        "facets": {"modal": proposal.modality,
                                   "modal_phrase": proposal.modal_phrase}}}
    return norm_contract.check_deontic(pair)


def _has_escalate(findings) -> bool:
    return any(f.level is Level.ESCALATE for f in findings)


def _has_violation(findings) -> bool:
    return any(f.level is Level.VIOLATION for f in findings)


# ── the op ────────────────────────────────────────────────────────────────────

def construct_norm(
    text: str,
    *,
    model: ModelFn,
    locus: str = "",
    risk_class: str = "C",
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> ConstructionResult:
    """Construct a grounded :class:`subsumption.Rule` from ``text``, or escalate.

    The ``model`` (an injected :data:`ports.ModelFn`) proposes a decomposition;
    deterministic gates over ``(proposal, text)`` then decide. The gates, in
    order of precedence:

      * **grounding** — any element whose span is not a substring of ``text`` is
        invented → REJECT (no Rule);
      * **well-formedness** — a proposal with no consequence / no condition is
        malformed → REJECT;
      * **faithfulness** — span-coverage over the operative content, plus NT-5
        (an absorbed exception). A gap → ESCALATE (flag for a human);
      * **audit** — :func:`interpret.audit` must find the decomposition sound;
        an inconsistent or unwarranted decomposition → ESCALATE;
      * **confidence floor** — NT-9 / :data:`CONFIDENCE_FLOOR`; sub-floor →
        ESCALATE, regardless of any single high score;
      * **discretion** — NT-4; a discretionary modality → ESCALATE.

    Only a proposal that is grounded AND faithful AND audited AND at/above the
    floor AND non-discretionary is ACCEPTED, and only then is a Rule returned.

    ``locus`` is an optional pinpoint (e.g. ``"Art. 17(1)"``) recorded as the
    Rule's source and in the provenance. It is a plain ``str`` — the solver is
    corpus-free and never receives a provision object.
    """
    prov: dict[str, Any] = {"locus": locus, "receipts": []}
    report: dict[str, Any] = {}

    # 0. Fill: consume the ModelFn seam and decode the proposal.
    raw = model(_build_prompt(text, locus))
    try:
        proposal = NormProposal.from_json(raw) if isinstance(raw, str) \
            else NormProposal.from_dict(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        report["decode"] = {"ok": False, "error": str(exc)}
        return _reject("model returned an undecodable proposal", report, prov)

    prov["receipts"] = [e.receipt(text) for e in proposal.all_elements()]

    # 1. Grounding (honesty floor #1): reject any invented span.
    invented = [e.span for e in proposal.all_elements() if not e.grounded_in(text)]
    report["grounding"] = {"ok": not invented, "invented": invented}
    if invented:
        return _reject(
            f"ungrounded element(s) — span not found in text: {invented!r}",
            report, prov)

    # 2. Well-formedness of the target Rule.
    cons_lit = proposal.consequence.literal if proposal.consequence else ""
    wf_ok = bool(cons_lit) and bool(proposal.elements)
    report["wellformed"] = {
        "ok": wf_ok,
        "reason": "" if wf_ok else "missing consequence or conditions",
    }
    if not wf_ok:
        return _reject("malformed proposal: " + report["wellformed"]["reason"],
                       report, prov)

    rule = Rule(
        id=f"norm:{locus}" if locus else "O26",
        conditions=tuple(e.literal for e in proposal.elements),
        consequence=cons_lit,
        exceptions=tuple(e.literal for e in proposal.exceptions),
        modality=proposal.modality,
        act=proposal.act or cons_lit,
        source=locus,
    )

    # 3. Faithfulness = span-coverage (honesty floor #2), plus NT-5.
    text_content = _content_tokens(text)
    claimed = set()
    for e in proposal.all_elements():
        claimed |= _content_tokens(e.span)
    uncovered = sorted(text_content - claimed)
    nt5 = _nt5_exception_finding(text, proposal)
    nt5_violation = _has_violation(nt5)
    faithful = (not uncovered) and (not nt5_violation)
    report["faithfulness"] = {
        "ok": faithful, "uncovered": uncovered,
        "nt5": [f.to_dict() for f in nt5],
    }
    if not faithful:
        why = ("operative content not covered: " + repr(uncovered)) if uncovered \
            else "absorbed exception (NT-5): the norm was not read to the end"
        return _escalate("faithfulness flag — " + why, report, prov)

    # 4. Audit: consume interpret.interpret + interpret.audit.
    audit_report = _audit_reasoning(text, proposal)
    audited = audit_report["verdict"] == "sound"
    report["audit"] = {"verdict": audit_report["verdict"],
                       "reasons": audit_report["reasons"]}
    if not audited:
        # Confidence is never trusted alone: an unsound decomposition escalates
        # no matter how high the self-reported score.
        return _escalate("audit unsound — " + "; ".join(audit_report["reasons"]),
                         report, prov)

    # 5. Confidence floor: NT-9 plus a hard floor independent of risk_class.
    min_conf = proposal.min_confidence()
    nt9 = _nt9_confidence_finding(min_conf, risk_class)
    sub_floor = min_conf < confidence_floor or _has_escalate(nt9)
    report["confidence"] = {"min": min_conf, "floor": confidence_floor,
                            "ok": not sub_floor, "nt9": [f.to_dict() for f in nt9]}
    if sub_floor:
        return _escalate(
            f"sub-floor confidence {min_conf} < {confidence_floor}", report, prov)

    # 6. Discretion: NT-4. A discretionary modality is a human's Ermessen.
    if proposal.modality:
        nt4 = _nt4_deontic_finding(proposal)
        report["deontic"] = {"escalate": _has_escalate(nt4),
                             "findings": [f.to_dict() for f in nt4]}
        if _has_escalate(nt4):
            return _escalate("discretionary modality — human Ermessen required",
                             report, prov)

    # 7. Accept — grounded, faithful, audited, at/above floor, non-discretionary.
    # Belt-and-suspenders: never hand back an ungrounded Rule.
    assert all(r["grounded"] for r in prov["receipts"]), \
        "invariant: accepted Rule has an ungrounded receipt"
    report["accepted"] = True
    return ConstructionResult("accepted", rule, False,
                              "grounded, faithful, audited and at/above the floor",
                              report, prov)
