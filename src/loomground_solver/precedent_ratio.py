# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Precedent ratio extraction (O143) — case-text → the *ratio decidendi* as a
grounded :class:`subsumption.Rule`, with the obiter kept separate, or an honest
ESCALATE. An [I]-tier op: the **model fills**, the **contract gates**, the harness
**escalates** the genuinely contestable.

A statute hands the solver a norm-text; a *case* hands it a court's reasoning, and
the hard, committed problem is telling the **binding ground** (the ratio decidendi
— the rule necessary to the holding) from the **obiter dicta** (remarks made in
passing, which bind nobody). Getting that line wrong is how a machine invents
precedent: it lifts an aside into a rule, or keeps a claim in the ratio that the
holding never needed. This module refuses to do either silently.

It is deliberately not a decider. A model proposes, over generic case-text:

  * the **ratio decidendi** — the rule the case stands for (a binding ground
    statement plus the operative conditions it turns on);
  * the **material facts** the ratio turns on, each tagged with the source span it
    was drawn from, a confidence, and whether it is *necessary to the holding*;
  * the **holding / disposition** (the Rechtsfolge the court actually ordered);
  * the **obiter dicta** — non-binding remarks, each span-tagged and kept apart.

Then a chain of **deterministic gates** over ``(proposal, case_text)`` decides
whether that proposal may become a Rule at all. It wraps what exists rather than
regrowing it:

  * the fill is the injected :data:`ports.ModelFn` (``str -> str``): the package
    never binds a model; the completion is a JSON proposal it decodes;
  * the reasoning is verified through :func:`interpret.interpret` (the fill seam,
    driven by the decoded proposal) and :func:`interpret.audit` (the solver
    catching an unwarranted leap or a self-contradictory decomposition);
  * the justification floor is the existing reasoning contract: R1 evidence
    (:func:`contract.check_evidence` — a material fact carries its source span),
    R2 warrant (:func:`contract.check_warrants` — the ratio move names its binding
    ground) and NT-9 confidence (:func:`norm_contract.check_confidence` /
    :data:`norm_contract.CONFIDENCE_FLOOR`);
  * the output shape is a plain :class:`subsumption.Rule`.

Precedent honesty is committed, not optional:

  1. **ratio ≠ obiter** — obiter is EXCLUDED from the extracted Rule; a proposed
     ratio element that the holding did not need (``necessary=False``) is
     reclassified and **FLAGGED**, never silently kept in the binding rule.
  2. **grounding** — every material-fact and ratio span must be a substring of the
     case-text. An ungrounded material fact is REJECTED as invented; the harness
     never returns an ungrounded ratio.
  3. **contestability** — if the model returns several defensible candidate ratios,
     or marks the ratio unclear, the op ESCALATES. It never fabricates a single
     ratio out of a genuine disagreement.
  4. **confidence is never trusted alone** — a high self-reported score cannot buy
     an acceptance past thin grounding, an unsound audit, or a missing warrant.

Pure stdlib (``json``, ``dataclasses``, ``typing``). No governance, no corpus, no
domain, and no dependency on ``loomground_legal``: :func:`extract_ratio` takes a
generic case-text ``str`` and optional ``court`` / ``level`` pinpoints ``str`` —
never a corpus-coupled decision object.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from . import contract
from . import norm_contract
from .interpret import audit as _audit, interpret as _interpret
from .norm_contract import CONFIDENCE_FLOOR, Level
from .ports import ModelFn
from .subsumption import Rule


# ── the proposal schema the ModelFn returns ───────────────────────────────────

@dataclass(frozen=True)
class RatioElement:
    """One decomposed piece of the court's reasoning: a solver ``literal``, the
    verbatim ``span`` it was drawn from, the model's ``confidence``, and — for a
    material fact — whether the holding actually *needed* it (``necessary``). A
    material fact the holding did not need is obiter-by-another-name."""

    span: str
    literal: str
    confidence: float = 1.0
    role: str = "material_fact"        # material_fact | holding | obiter
    necessary: bool = True             # was this necessary to the holding?

    @classmethod
    def from_dict(cls, d: dict, *, role: str = "material_fact") -> "RatioElement":
        return cls(span=str(d.get("span", "")),
                   literal=str(d.get("literal", "")),
                   confidence=float(d.get("confidence", 1.0)),
                   role=str(d.get("role", role)),
                   necessary=bool(d.get("necessary", True)))

    def grounded_in(self, text: str) -> bool:
        """Honesty floor: the span must be a substring of the case-text."""
        return bool(self.span) and self.span in text

    def receipt(self, text: str) -> dict[str, Any]:
        """A provenance receipt: where in the case-text this element is anchored."""
        start = text.find(self.span) if self.span else -1
        end = start + len(self.span) if start >= 0 else -1
        return {"role": self.role, "literal": self.literal, "span": self.span,
                "start": start, "end": end, "confidence": self.confidence,
                "necessary": self.necessary, "grounded": start >= 0}


@dataclass(frozen=True)
class RatioProposal:
    """A model's proposed reading of a case. Convention, not truth — every field is
    subject to the gates before any of it becomes a Rule.

    ``candidate_ratios`` and ``ratio_unclear`` are the *contestability* signals: a
    model that sees more than one defensible ratio should say so (list them), and a
    model unsure the case even has a single ratio should set the flag — either one
    makes the op ESCALATE rather than fabricate a single rule."""

    ratio_statement: str = ""                        # the binding ground (the warrant)
    material_facts: tuple[RatioElement, ...] = ()     # the facts the ratio turns on
    holding: Optional[RatioElement] = None            # the disposition (Rechtsfolge)
    obiter: tuple[RatioElement, ...] = ()             # non-binding remarks, kept apart
    candidate_ratios: tuple[str, ...] = ()            # >1 ⇒ contestable ⇒ ESCALATE
    ratio_unclear: bool = False                       # model unsure ⇒ ESCALATE

    @classmethod
    def from_dict(cls, d: dict) -> "RatioProposal":
        hold = d.get("holding")
        return cls(
            ratio_statement=str(d.get("ratio_statement", "")),
            material_facts=tuple(RatioElement.from_dict(e, role="material_fact")
                                 for e in (d.get("material_facts") or ())),
            holding=(RatioElement.from_dict(hold, role="holding")
                     if hold else None),
            obiter=tuple(RatioElement.from_dict(e, role="obiter")
                         for e in (d.get("obiter") or ())),
            candidate_ratios=tuple(str(c) for c in (d.get("candidate_ratios") or ())),
            ratio_unclear=bool(d.get("ratio_unclear", False)),
        )

    @classmethod
    def from_json(cls, raw: str) -> "RatioProposal":
        return cls.from_dict(json.loads(raw))

    def necessary_facts(self) -> list[RatioElement]:
        """Material facts the holding needed — the operative conditions of the Rule."""
        return [e for e in self.material_facts if e.necessary]

    def unnecessary_facts(self) -> list[RatioElement]:
        """Material facts placed in the ratio that the holding did NOT need — these
        are flagged and reclassified, never kept in the binding rule."""
        return [e for e in self.material_facts if not e.necessary]

    def rule_elements(self) -> list[RatioElement]:
        """The elements that would actually enter the Rule (necessary facts +
        holding). Obiter and unnecessary facts are excluded by construction."""
        out = list(self.necessary_facts())
        if self.holding is not None:
            out.append(self.holding)
        return out

    def min_confidence(self) -> float:
        confs = [e.confidence for e in self.rule_elements()]
        return min(confs) if confs else 0.0


# ── the model port: a deterministic stub for tests ────────────────────────────

class StubModel:
    """A deterministic :data:`ports.ModelFn` (``str -> str``): it ignores the prompt
    and returns a *fixed* canned case reading as JSON. Faithful to the real seam —
    a host's model likewise returns a completion string that :func:`extract_ratio`
    decodes — but with no model runtime, so the gates are exercised
    deterministically. Construct with the reading you want proposed::

        model = StubModel({"ratio_statement": "...", "material_facts": [...],
                           "holding": {...}, "obiter": [...]})
    """

    def __init__(self, proposal: dict):
        self._payload = json.dumps(proposal)

    def __call__(self, prompt: str) -> str:   # ports.ModelFn
        return self._payload


def _build_prompt(text: str, court: str, level: str) -> str:
    """The instruction handed to the model. Content is irrelevant to the gates (a
    real model reads it; :class:`StubModel` ignores it) — but the call is a genuine
    ``ModelFn`` invocation, so the seam is consumed, not bypassed."""
    tag = " / ".join(p for p in (court, level) if p)
    head = f"Read the following case{f' ({tag})' if tag else ''} and separate its "
    return (head + "ratio decidendi from its obiter dicta. Return the binding "
            "ground statement, the material facts the ratio turns on (each with "
            "its verbatim source SPAN, a solver literal, a confidence, and whether "
            "it was necessary to the holding), the holding, and the obiter dicta. "
            "If more than one defensible ratio is available, list them in "
            "candidate_ratios and do not choose. Reply as JSON.\n\n" + text)


# ── the result ────────────────────────────────────────────────────────────────

@dataclass
class RatioResult:
    """The outcome of a ratio-extraction attempt. It carries a grounded ratio-Rule
    XOR an escalation/rejection — never an ungrounded ratio, and never a rule built
    from obiter. The ``obiter`` and ``flagged`` tuples are kept separate from the
    Rule on purpose: the reader can see what was *excluded* and why."""

    status: str                                   # extracted | rejected | escalated
    rule: Optional[Rule]
    material_facts: tuple[dict, ...] = ()          # the grounded, necessary facts
    holding: str = ""
    obiter: tuple[dict, ...] = ()                  # non-binding remarks, kept SEPARATE
    flagged: tuple[dict, ...] = ()                 # ratio elements not necessary → flagged
    court: str = ""
    level: str = ""
    escalated: bool = False
    reason: str = ""
    gate_report: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def extracted(self) -> bool:
        return self.status == "extracted"

    @property
    def rejected(self) -> bool:
        return self.status == "rejected"


def _reject(reason: str, report: dict, prov: dict, **kw) -> RatioResult:
    return RatioResult("rejected", None, reason=reason, gate_report=report,
                       provenance=prov, escalated=False, **kw)


def _escalate(reason: str, report: dict, prov: dict, **kw) -> RatioResult:
    return RatioResult("escalated", None, reason=reason, gate_report=report,
                       provenance=prov, escalated=True, **kw)


# ── the reasoning-audit bridge (consumes interpret.interpret + interpret.audit)─

def _proposal_to_interp(proposal: RatioProposal) -> dict:
    """Cast the ratio as facts + a rule + a candidate so the existing auditor can
    check it: the necessary material facts are taken as facts, the ratio is
    ``facts => holding``, and the candidate is the holding. A self-contradictory
    reading (a material fact that negates the holding, ``x`` and ``-x``) then comes
    back inconsistent; a holding the facts cannot reach comes back unwarranted — the
    solver catching an incoherent reading of the case."""
    conds = tuple(e.literal for e in proposal.necessary_facts())
    hold = proposal.holding.literal if proposal.holding else None
    rule = Rule(id="O143", conditions=conds, consequence=hold or "")
    return {"facts": set(conds), "rules": [rule], "candidate": hold}


def _audit_reasoning(text: str, proposal: RatioProposal) -> dict:
    """Fill through :func:`interpret.interpret` (its ``parse`` seam driven by the
    decoded proposal) then verify with :func:`interpret.audit`."""
    interp = _interpret(text, parse=lambda _t: _proposal_to_interp(proposal))
    return _audit(interp)


# ── the reasoning-contract bridges (consume the existing gate functions) ───────

def _as_caserecord(proposal: RatioProposal, court: str, level: str) -> dict:
    """Shape the reading as a :mod:`contract`-readable case dict so the existing R1
    (evidence) and R2 (warrant) gates can run: each necessary material fact is a
    sourced FACT (its span is the source), and the ratio move is a single chain
    step whose warrant is the binding-ground statement. A material fact without a
    span → R1 VIOLATION; a ratio with no stated binding ground → R2 ESCALATE."""
    facts = [{"text": e.literal, "source": e.span} for e in proposal.necessary_facts()]
    pinpoint = " / ".join(p for p in (court, level) if p)
    hold = proposal.holding.literal if proposal.holding else ""
    chain = [{"step": "ratio", "text": hold, "warrant": proposal.ratio_statement}]
    return {"problem": {"text": pinpoint or "precedent"},
            "facts": facts, "grounds": [], "chain": chain,
            "resolution": {"type": "determinate", "answer": hold}}


def _nt9_confidence_finding(min_conf: float, risk_class: str):
    """NT-9 via :func:`norm_contract.check_confidence`."""
    pair = {"id": "O143", "solution": {"confidence": min_conf}}
    return norm_contract.check_confidence(pair, risk_class=risk_class)


def _has(findings, lvl: Level) -> bool:
    return any(f.level is lvl for f in findings)


# ── the op ────────────────────────────────────────────────────────────────────

def extract_ratio(
    case_text: str,
    *,
    model: ModelFn,
    court: str = "",
    level: str = "",
    risk_class: str = "C",
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> RatioResult:
    """Extract the ratio decidendi of ``case_text`` as a grounded
    :class:`subsumption.Rule`, or escalate / reject.

    The ``model`` (an injected :data:`ports.ModelFn`) proposes a reading;
    deterministic gates over ``(proposal, case_text)`` then decide. The gates, in
    order of precedence:

      * **grounding** — any material-fact or holding span that is not a substring of
        ``case_text`` is invented → REJECT (no Rule);
      * **contestability** — more than one defensible candidate ratio, or the ratio
        marked unclear → ESCALATE (never fabricate one from a genuine dispute);
      * **ratio/obiter separation** — obiter is EXCLUDED from the Rule; a material
        fact the holding did not need (``necessary=False``) is reclassified and
        FLAGGED, never kept in the binding rule;
      * **well-formedness** — after the flag pass there must be ≥1 necessary
        condition and a holding, or the ratio is not determinable → ESCALATE;
      * **evidence + warrant** — R1 (:func:`contract.check_evidence`): a material
        fact carries its source span; R2 (:func:`contract.check_warrants`): the
        ratio move names its binding ground. A missing source → REJECT; a missing
        binding ground → ESCALATE;
      * **audit** — :func:`interpret.audit` must find the reading sound; an
        inconsistent or unwarranted reading → ESCALATE;
      * **confidence floor** — NT-9 / :data:`CONFIDENCE_FLOOR`; sub-floor →
        ESCALATE, regardless of any single high score.

    Only a reading that is grounded AND uncontested AND well-formed AND evidenced
    AND warranted AND audited AND at/above the floor yields a Rule — and even then
    the obiter and any flagged unnecessary elements are returned *separately*, never
    folded into the Rule.

    ``court`` / ``level`` are optional pinpoints (e.g. ``"BGH"`` / ``"appellate"``)
    recorded as the Rule's source and in the provenance. They are plain ``str`` —
    the solver is corpus-free and never receives a decision object.
    """
    prov: dict[str, Any] = {"court": court, "level": level, "receipts": []}
    report: dict[str, Any] = {}
    pin = " / ".join(p for p in (court, level) if p)

    # 0. Fill: consume the ModelFn seam and decode the proposed reading.
    raw = model(_build_prompt(case_text, court, level))
    try:
        proposal = RatioProposal.from_json(raw) if isinstance(raw, str) \
            else RatioProposal.from_dict(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        report["decode"] = {"ok": False, "error": str(exc)}
        return _reject("model returned an undecodable proposal", report, prov,
                       court=court, level=level)

    all_elems = (list(proposal.material_facts)
                 + ([proposal.holding] if proposal.holding else [])
                 + list(proposal.obiter))
    prov["receipts"] = [e.receipt(case_text) for e in all_elems]
    prov["candidate_ratios"] = list(proposal.candidate_ratios)
    prov["ratio_statement"] = proposal.ratio_statement

    # Obiter is separated from the very first, and carried through untouched. It is
    # NEVER a source of Rule content — only reported, so the reader sees what the
    # court said in passing and that it was set aside.
    obiter_out = tuple(e.receipt(case_text) for e in proposal.obiter)

    # 1. Grounding (honesty floor): reject any invented material-fact / holding span.
    #    Obiter spans are reported but never gate — a mis-grounded aside is not a
    #    reason to reject a sound ratio; it is simply not binding either way.
    binding = list(proposal.material_facts) + ([proposal.holding] if proposal.holding else [])
    invented = [e.span for e in binding if not e.grounded_in(case_text)]
    report["grounding"] = {"ok": not invented, "invented": invented}
    if invented:
        return _reject(
            f"ungrounded material fact/holding — span not found in case-text: "
            f"{invented!r}", report, prov, obiter=obiter_out, court=court, level=level)

    # 2. Contestability: more than one defensible ratio, or an unclear ratio, is a
    #    human's call. Do NOT fabricate a single ratio out of a genuine dispute.
    contested = len(proposal.candidate_ratios) > 1
    report["contestability"] = {
        "ok": not (contested or proposal.ratio_unclear),
        "candidate_ratios": list(proposal.candidate_ratios),
        "unclear": proposal.ratio_unclear,
    }
    if contested:
        return _escalate(
            "multiple defensible candidate ratios — the binding ground is "
            f"contestable ({len(proposal.candidate_ratios)} candidates)",
            report, prov, obiter=obiter_out, court=court, level=level)
    if proposal.ratio_unclear:
        return _escalate("the ratio is unclear — no single binding ground to extract",
                         report, prov, obiter=obiter_out, court=court, level=level)

    # 3. Ratio/obiter separation: a material fact the holding did not NEED is not
    #    ratio — it is flagged and reclassified, never kept in the binding rule.
    flagged = tuple(e.receipt(case_text) for e in proposal.unnecessary_facts())
    report["necessity"] = {
        "flagged": [dict(r, reason="not necessary to the holding") for r in flagged],
        "necessary": [e.literal for e in proposal.necessary_facts()],
    }

    # 4. Well-formedness: after the flag pass, a Rule needs ≥1 condition and a
    #    holding. Nothing left ⇒ there is no determinable ratio ⇒ escalate.
    necessary = proposal.necessary_facts()
    hold_lit = proposal.holding.literal if proposal.holding else ""
    wf_ok = bool(necessary) and bool(hold_lit)
    report["wellformed"] = {
        "ok": wf_ok,
        "reason": "" if wf_ok else "no necessary material fact, or no holding",
    }
    if not wf_ok:
        return _escalate(
            "no determinable ratio: " + report["wellformed"]["reason"],
            report, prov, obiter=obiter_out, flagged=flagged,
            court=court, level=level)

    # 5. Evidence (R1) + warrant (R2): consume the reasoning-contract gates.
    case = _as_caserecord(proposal, court, level)
    ev = contract.check_evidence(case)
    wa = contract.check_warrants(case)
    report["evidence"] = {"violation": _has(ev, Level.VIOLATION),
                          "findings": [f.to_dict() for f in ev]}
    report["warrant"] = {"escalate": _has(wa, Level.ESCALATE),
                         "findings": [f.to_dict() for f in wa]}
    if _has(ev, Level.VIOLATION):
        return _reject("evidence gate (R1) — a material fact carries no source span",
                       report, prov, obiter=obiter_out, flagged=flagged,
                       court=court, level=level)
    if _has(wa, Level.ESCALATE):
        # The case states no binding ground for the move — a human must supply what
        # licenses treating this as the ratio. Confidence cannot buy past this.
        return _escalate("warrant gate (R2) — the ratio names no binding ground "
                         "(what licenses this rule?)",
                         report, prov, obiter=obiter_out, flagged=flagged,
                         court=court, level=level)

    # 6. Audit: consume interpret.interpret + interpret.audit. An inconsistent or
    #    unwarranted reading escalates no matter how high the self-reported score.
    audit_report = _audit_reasoning(case_text, proposal)
    audited = audit_report["verdict"] == "sound"
    report["audit"] = {"verdict": audit_report["verdict"],
                       "reasons": audit_report["reasons"]}
    if not audited:
        return _escalate("audit unsound — " + "; ".join(audit_report["reasons"]),
                         report, prov, obiter=obiter_out, flagged=flagged,
                         court=court, level=level)

    # 7. Confidence floor: NT-9 plus a hard floor independent of risk_class.
    #    Confidence is never trusted alone — it is the LAST gate, not the first.
    min_conf = proposal.min_confidence()
    nt9 = _nt9_confidence_finding(min_conf, risk_class)
    sub_floor = min_conf < confidence_floor or _has(nt9, Level.ESCALATE)
    report["confidence"] = {"min": min_conf, "floor": confidence_floor,
                            "ok": not sub_floor, "nt9": [f.to_dict() for f in nt9]}
    if sub_floor:
        return _escalate(
            f"sub-floor confidence {min_conf} < {confidence_floor}",
            report, prov, obiter=obiter_out, flagged=flagged,
            court=court, level=level)

    # 8. Extract — grounded, uncontested, well-formed, evidenced, warranted,
    #    audited and at/above the floor. The Rule is built from the NECESSARY
    #    material facts only; obiter and flagged elements are handed back separately.
    rule = Rule(
        id=f"ratio:{pin}" if pin else "O143",
        conditions=tuple(e.literal for e in necessary),
        consequence=hold_lit,
        source=pin,
    )
    mat_out = tuple(e.receipt(case_text) for e in necessary)

    # Belt-and-suspenders: the accepted Rule must be fully grounded and must carry
    # no obiter/flagged literal in its conditions or consequence.
    assert all(r["grounded"] for r in mat_out), \
        "invariant: extracted ratio has an ungrounded material fact"
    excluded_lits = {r["literal"] for r in obiter_out} | {r["literal"] for r in flagged}
    assert not (set(rule.conditions) | {rule.consequence}) & excluded_lits, \
        "invariant: obiter/flagged content leaked into the ratio Rule"

    report["extracted"] = True
    return RatioResult(
        "extracted", rule,
        material_facts=mat_out,
        holding=hold_lit,
        obiter=obiter_out,
        flagged=flagged,
        court=court, level=level,
        escalated=False,
        reason=("ratio grounded, uncontested, evidenced, warranted, audited and "
                "at/above the floor; obiter excluded"
                + (f"; {len(flagged)} unnecessary element(s) flagged" if flagged else "")),
        gate_report=report, provenance=prov)
