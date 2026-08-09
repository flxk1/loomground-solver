# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Causal construction (the CAUSAL fact-dimension) — policy text → a *grounded*
causal model (cause → effect edges, optionally via a mechanism), or an honest
REJECT / ESCALATE. An [I]-tier op: the **model fills** the causal model, the
**contract gates** it, the harness **escalates** the open — and for the causal
dimension the escalate is the *common* honest outcome, because a statute usually
*presupposes* its causal mechanism rather than writing it down.

Sibling to :mod:`norm_construction` (which builds one :class:`subsumption.Rule`)
and :mod:`structural_construction` (which builds a STRUCTURAL subgraph). This op
builds the *causal* subgraph a policy text implies — the "X causes / triggers /
enables / prevents Y" links it asserts — and hands back a subgraph of
:class:`reasoning.Edge` all tagged :data:`dimensions.Dimension.CAUSAL`. It is
deliberately not a decider: a model proposes causal links, **each tagged with a
STATUS** — ``STATED`` (asserted in the text, with a source span) or
``PRESUPPOSED`` (the mechanism the statute assumes but does not write) — a
confidence, and whether the link is *load-bearing*; then a chain of
**deterministic gates** decides whether that proposal may become a grounded
subgraph at all.

It wraps what exists rather than regrowing it:

  * the fill is the injected :data:`ports.ModelFn` (``str -> str``): the package
    never binds a model; the completion is a JSON proposal it decodes;
  * the reasoning is verified through :func:`interpret.interpret` (the fill seam,
    driven here by the decoded proposal) and :func:`interpret.audit` (the solver
    catching a self-contradictory causal model, e.g. ``X`` causing both ``Y``
    and ``not-Y``) — the audit is *not* reimplemented;
  * the confidence floor is the existing contract:
    :func:`norm_contract.check_confidence` / :data:`norm_contract.CONFIDENCE_FLOOR`;
  * the output edge shape is the existing dimensioned :class:`reasoning.Edge`,
    every grounded one tagged :data:`dimensions.Dimension.CAUSAL`.

The causal-honesty floor is committed, not optional — it is the load-bearing
gate of this op:

  1. **grounding of STATED links** — every STATED link's cause / effect /
     mechanism span must be a *substring of the input text*. A STATED link whose
     span is not found is REJECTED as invented. The harness never asserts an
     ungrounded causal fact.
  2. **presupposition honesty** — a PRESUPPOSED link (the mechanism the statute
     assumes but does not write) is **marked INCOMPLETE** and kept **out of the
     grounded set**. It is *surfaced*, never asserted as a grounded fact — you
     cannot ground what the statute only assumes.
  3. **materiality** — if any *load-bearing* causal link is PRESUPPOSED (or the
     model has no grounded link at all, only assumed ones), the whole result
     ESCALATES: the causal model is materially presupposed and cannot stand as
     extracted fact.
  4. **confidence is never trusted alone** — a high self-reported score cannot
     buy an acceptance past an unsound audit or a materially-presupposed model;
     sub-floor confidence over the STATED links ESCALATES regardless.

Pure stdlib (``json``, ``dataclasses``, ``typing``). No governance, no corpus,
no domain: :func:`construct_causal` takes a generic policy-text ``str`` — never a
corpus-coupled provision object. The solver is corpus-free; this op imports
neither ``loomground_legal`` nor ``loomground_versum``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from . import norm_contract
from .dimensions import Dimension
from .interpret import audit as _audit_interp
from .interpret import interpret as _interpret
from .norm_contract import CONFIDENCE_FLOOR, Level
from .ports import ModelFn
from .reasoning import Edge
from .subsumption import Rule


# ── the causal statuses ───────────────────────────────────────────────────────
# The single new distinction this op adds over its structural/norm siblings: a
# proposed link is either ASSERTED in the text (STATED) or ASSUMED by the statute
# but never written (PRESUPPOSED). The gates treat the two categorically
# differently — only STATED links can ground; PRESUPPOSED links are surfaced.

STATED = "stated"
PRESUPPOSED = "presupposed"
_STATUSES = (STATED, PRESUPPOSED)


# ── the proposal schema the ModelFn returns ───────────────────────────────────

@dataclass(frozen=True)
class CausalClaim:
    """One proposed causal link: ``cause`` → ``effect`` (optionally *via* a
    ``mechanism``), with a STATUS, the verbatim source spans (for a STATED link)
    and the model's confidence. ``load_bearing`` records whether the statute's
    operation *depends* on this link — the materiality gate reads it."""

    cause: str
    effect: str
    status: str = STATED                 # stated | presupposed
    cause_span: str = ""
    effect_span: str = ""
    mechanism: str = ""                  # optional mechanism literal
    mechanism_span: str = ""
    confidence: float = 1.0
    load_bearing: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "CausalClaim":
        status = str(d.get("status", STATED)).strip().lower()
        return cls(
            cause=str(d.get("cause", "")),
            effect=str(d.get("effect", "")),
            status=status if status in _STATUSES else status,  # kept, validated later
            cause_span=str(d.get("cause_span", "")),
            effect_span=str(d.get("effect_span", "")),
            mechanism=str(d.get("mechanism", "")),
            mechanism_span=str(d.get("mechanism_span", "")),
            confidence=float(d.get("confidence", 1.0)),
            load_bearing=bool(d.get("load_bearing", False)),
        )

    @property
    def is_stated(self) -> bool:
        return self.status == STATED

    @property
    def is_presupposed(self) -> bool:
        return self.status == PRESUPPOSED

    def required_spans(self) -> tuple[str, ...]:
        """The spans that must ground a STATED link: cause, effect, and the
        mechanism span iff a mechanism was named. (Empty for a PRESUPPOSED link —
        there is nothing in the text to ground.)"""
        spans = [self.cause_span, self.effect_span]
        if self.mechanism:
            spans.append(self.mechanism_span)
        return tuple(spans)

    def ungrounded_spans(self, text: str) -> list[str]:
        """Honesty floor #1: for a STATED link, which required spans are *not* a
        substring of ``text`` (invented). Always empty for a PRESUPPOSED link."""
        if not self.is_stated:
            return []
        return [s for s in self.required_spans() if not (s and s in text)]

    def well_formed(self) -> bool:
        return bool(self.cause) and bool(self.effect) and self.status in _STATUSES

    def receipt(self, text: str) -> dict[str, Any]:
        """A provenance receipt: where each span anchors, and the status."""
        def _anchor(span: str) -> dict[str, Any]:
            start = text.find(span) if span else -1
            return {"span": span, "start": start,
                    "end": start + len(span) if start >= 0 else -1,
                    "grounded": start >= 0}
        return {
            "cause": self.cause, "effect": self.effect,
            "mechanism": self.mechanism, "status": self.status,
            "load_bearing": self.load_bearing, "confidence": self.confidence,
            "cause_span": _anchor(self.cause_span),
            "effect_span": _anchor(self.effect_span),
            "mechanism_span": _anchor(self.mechanism_span) if self.mechanism else None,
        }

    def to_edge(self, source_pair: str) -> Edge:
        """Cast a STATED+grounded link as a dimensioned :class:`reasoning.Edge`,
        tagged :data:`dimensions.Dimension.CAUSAL`. The predicate is the named
        mechanism, or the neutral ``"causes"`` when none was written."""
        return Edge(
            subject=self.cause,
            predicate=self.mechanism or "causes",
            object=self.effect,
            dimension=Dimension.CAUSAL,
            weight=max(0.0, min(1.0, self.confidence)),
            source_pair=source_pair,
        )


@dataclass(frozen=True)
class PresupposedLink:
    """A surfaced-but-not-grounded causal link: the mechanism the statute assumes
    and does not write. Always ``incomplete=True`` — it is never a grounded
    fact, only an honestly-marked open."""

    cause: str
    effect: str
    mechanism: str = ""
    load_bearing: bool = False
    confidence: float = 1.0
    incomplete: bool = True
    reason: str = "presupposed by the statute; not written and not grounded"

    @classmethod
    def from_claim(cls, c: CausalClaim) -> "PresupposedLink":
        return cls(cause=c.cause, effect=c.effect, mechanism=c.mechanism,
                   load_bearing=c.load_bearing, confidence=c.confidence)

    def as_dict(self) -> dict[str, Any]:
        return {"cause": self.cause, "effect": self.effect,
                "mechanism": self.mechanism, "load_bearing": self.load_bearing,
                "confidence": self.confidence, "incomplete": self.incomplete,
                "reason": self.reason}


@dataclass(frozen=True)
class CausalProposal:
    """A model's proposed causal model. Convention, not truth — every link is
    subject to the gates before any of it becomes a grounded Edge."""

    claims: tuple[CausalClaim, ...] = ()

    @classmethod
    def from_dict(cls, d: dict) -> "CausalProposal":
        raw = d.get("claims") or d.get("edges") or ()
        return cls(claims=tuple(CausalClaim.from_dict(c) for c in raw))

    @classmethod
    def from_json(cls, raw: str) -> "CausalProposal":
        return cls.from_dict(json.loads(raw))

    def stated(self) -> list[CausalClaim]:
        return [c for c in self.claims if c.is_stated]

    def presupposed(self) -> list[CausalClaim]:
        return [c for c in self.claims if c.is_presupposed]


# ── the model port: a deterministic stub for tests ────────────────────────────

class StubModel:
    """A deterministic :data:`ports.ModelFn` (``str -> str``): it ignores the
    prompt and returns a *fixed* canned causal model as JSON. Faithful to the
    real seam — a host's model likewise returns a completion string that
    :func:`construct_causal` decodes — but with no model runtime, so the gates
    are exercised deterministically. Construct with the proposal to propose::

        model = StubModel({"claims": [{"cause": ..., "effect": ...}, ...]})
    """

    def __init__(self, proposal: dict):
        self._payload = json.dumps(proposal)

    def __call__(self, prompt: str) -> str:   # ports.ModelFn
        return self._payload


def _build_prompt(text: str) -> str:
    """The instruction handed to the model. Content is irrelevant to the gates
    (a real model reads it; :class:`StubModel` ignores it) — but the call is a
    genuine ``ModelFn`` invocation, so the seam is consumed, not bypassed."""
    return (
        "Extract the causal model of the following policy text. For each causal "
        "link give cause, effect, an optional mechanism, a STATUS of 'stated' "
        "(asserted in the text — supply the verbatim cause/effect/mechanism "
        "SPANS) or 'presupposed' (assumed by the statute but not written), "
        "whether the link is load_bearing, and a confidence. Reply as JSON.\n\n"
        + text
    )


# ── the result ────────────────────────────────────────────────────────────────

@dataclass
class CausalResult:
    """The outcome of a causal-construction attempt. It carries the grounded
    causal subgraph (STATED + grounded, CAUSAL-tagged) together with the
    honestly-marked presupposed set — XOR a rejection / escalation. It never
    presents a presupposed link as grounded, and never an ungrounded STATED
    link."""

    status: str                                  # extracted | rejected | escalated
    grounded_edges: tuple[Edge, ...]
    presupposed: tuple[PresupposedLink, ...]
    escalated: bool
    reason: str
    gate_report: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def extracted(self) -> bool:
        return self.status == "extracted"

    @property
    def rejected(self) -> bool:
        return self.status == "rejected"


def _reject(reason, report, prov, presupposed=()) -> CausalResult:
    return CausalResult("rejected", (), tuple(presupposed), False, reason,
                        report, prov)


def _escalate(reason, report, prov, presupposed=()) -> CausalResult:
    return CausalResult("escalated", (), tuple(presupposed), True, reason,
                        report, prov)


# ── the reasoning-audit bridge (consumes interpret.interpret + interpret.audit)─

def _stated_to_interp(stated: list[CausalClaim]) -> dict:
    """Cast the STATED causal links as facts + rules so the existing auditor can
    check them: each cause is a fact, each link is a rule ``cause => effect``. A
    causal model where ``X`` is said to both cause ``Y`` and cause ``not-Y`` then
    closes to a clashing set and comes back inconsistent — the solver catching an
    incoherent causal model, without this module reimplementing the check."""
    facts: set[str] = set()
    rules: list[Rule] = []
    for i, c in enumerate(stated):
        facts.add(c.cause)
        rules.append(Rule(id=f"causal:{i}", conditions=(c.cause,),
                          consequence=c.effect))
    return {"facts": facts, "rules": rules, "candidate": None}


def _audit_reasoning(text: str, stated: list[CausalClaim]) -> dict:
    """Fill through :func:`interpret.interpret` (its ``parse`` seam driven by the
    decoded proposal) then verify with :func:`interpret.audit`."""
    interp = _interpret(text, parse=lambda _t: _stated_to_interp(stated))
    return _audit_interp(interp)


# ── the norm-contract bridge (consumes the existing confidence gate) ──────────

def _confidence_finding(min_conf: float, risk_class: str):
    """NT-9 via :func:`norm_contract.check_confidence`."""
    pair = {"id": "causal", "solution": {"confidence": min_conf}}
    return norm_contract.check_confidence(pair, risk_class=risk_class)


def _has_escalate(findings) -> bool:
    return any(f.level is Level.ESCALATE for f in findings)


# ── the op ────────────────────────────────────────────────────────────────────

def construct_causal(
    text: str,
    *,
    model: ModelFn,
    risk_class: str = "C",
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> CausalResult:
    """Construct a grounded causal subgraph from ``text``, or reject / escalate.

    The ``model`` (an injected :data:`ports.ModelFn`) proposes a causal model;
    deterministic gates over ``(proposal, text)`` then decide. The gates, in
    order of precedence:

      * **grounding of STATED links** — any STATED link whose cause / effect /
        mechanism span is not a substring of ``text`` is invented → REJECT (no
        edge is returned);
      * **well-formedness** — a link with no cause / no effect / an unknown
        status is malformed → REJECT;
      * **presupposition honesty** — PRESUPPOSED links are partitioned out,
        marked INCOMPLETE, and never enter the grounded set;
      * **materiality** — a *load-bearing* PRESUPPOSED link (or a model with no
        grounded link at all, only assumed ones) → ESCALATE: the causal model is
        materially presupposed and cannot stand as extracted fact;
      * **audit** — :func:`interpret.audit` must find the STATED model coherent;
        a self-contradictory causal model (``X`` causing ``Y`` and ``not-Y``) →
        ESCALATE, regardless of confidence;
      * **confidence floor** — NT-9 / :data:`CONFIDENCE_FLOOR` over the STATED
        links; sub-floor → ESCALATE.

    Only a proposal that grounds every STATED link, is not materially
    presupposed, audits coherent and sits at/above the floor is EXTRACTED — and
    even then the result carries the presupposed links honestly, marked
    incomplete and outside the grounded set. Escalation is a pass, and for the
    causal dimension it is the common honest outcome.
    """
    prov: dict[str, Any] = {"receipts": []}
    report: dict[str, Any] = {}

    # 0. Fill: consume the ModelFn seam and decode the proposal.
    raw = model(_build_prompt(text))
    try:
        proposal = CausalProposal.from_json(raw) if isinstance(raw, str) \
            else CausalProposal.from_dict(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        report["decode"] = {"ok": False, "error": str(exc)}
        return _reject("model returned an undecodable proposal", report, prov)

    prov["receipts"] = [c.receipt(text) for c in proposal.claims]

    # 1. Well-formedness of every proposed link.
    malformed = [
        {"cause": c.cause, "effect": c.effect, "status": c.status}
        for c in proposal.claims if not c.well_formed()
    ]
    report["wellformed"] = {"ok": not malformed, "malformed": malformed}
    if malformed:
        return _reject(
            f"malformed causal link(s) — missing cause/effect or unknown status: "
            f"{malformed!r}", report, prov)

    # 2. Grounding (honesty floor #1): reject any invented STATED span.
    invented: list[str] = []
    for c in proposal.stated():
        invented.extend(c.ungrounded_spans(text))
    report["grounding"] = {"ok": not invented, "invented": invented}
    if invented:
        return _reject(
            f"ungrounded STATED link(s) — span not found in text: {invented!r}",
            report, prov)

    # 3. Presupposition honesty (honesty floor #2): partition the presupposed
    #    links out; they are surfaced, marked incomplete, never grounded.
    presupposed_claims = proposal.presupposed()
    presupposed = tuple(PresupposedLink.from_claim(c) for c in presupposed_claims)
    stated = proposal.stated()
    report["presupposition"] = {
        "stated": len(stated),
        "presupposed": len(presupposed),
        "links": [p.as_dict() for p in presupposed],
    }

    # 4. Materiality: cannot ground what the statute only assumes. A load-bearing
    #    presupposed link — or a model with nothing grounded at all — escalates.
    material_presupposed = [p for p in presupposed if p.load_bearing]
    nothing_grounded = (not stated) and bool(presupposed)
    materially_presupposed = bool(material_presupposed) or nothing_grounded
    report["materiality"] = {
        "ok": not materially_presupposed,
        "load_bearing_presupposed": [p.as_dict() for p in material_presupposed],
        "nothing_grounded": nothing_grounded,
    }
    if materially_presupposed:
        why = ("no STATED link grounds the model — it is entirely presupposed"
               if nothing_grounded else
               "a load-bearing causal link is presupposed, not written")
        return _escalate(
            "materially presupposed — " + why + "; cannot ground what the "
            "statute only assumes", report, prov, presupposed=presupposed)

    # 5. Audit: consume interpret.interpret + interpret.audit over the STATED
    #    model. Confidence is never trusted alone — an incoherent model escalates
    #    no matter how high the self-reported score.
    audit_report = _audit_reasoning(text, stated)
    audited = audit_report["verdict"] == "sound"
    report["audit"] = {"verdict": audit_report["verdict"],
                       "reasons": audit_report["reasons"]}
    if not audited:
        return _escalate(
            "audit unsound — " + "; ".join(audit_report["reasons"]),
            report, prov, presupposed=presupposed)

    # 6. Confidence floor: NT-9 plus a hard floor independent of risk_class,
    #    over the STATED links (the ones that would ground).
    stated_confs = [c.confidence for c in stated]
    min_conf = min(stated_confs) if stated_confs else 0.0
    nt9 = _confidence_finding(min_conf, risk_class)
    sub_floor = min_conf < confidence_floor or _has_escalate(nt9)
    report["confidence"] = {"min": min_conf, "floor": confidence_floor,
                            "ok": not sub_floor,
                            "nt9": [f.to_dict() for f in nt9]}
    if sub_floor:
        return _escalate(
            f"sub-floor confidence {min_conf} < {confidence_floor}",
            report, prov, presupposed=presupposed)

    # 7. Extract — every STATED link grounded, not materially presupposed,
    #    audited coherent and at/above the floor. Belt-and-suspenders: every
    #    grounded edge really is CAUSAL-tagged and STATED-grounded.
    grounded_edges = tuple(
        c.to_edge(f"causal:{i}") for i, c in enumerate(stated)
    )
    assert all(e.dimension is Dimension.CAUSAL for e in grounded_edges), \
        "invariant: a grounded causal edge is not CAUSAL-tagged"
    report["extracted"] = {"grounded_edges": len(grounded_edges),
                           "presupposed": len(presupposed)}
    return CausalResult(
        "extracted", grounded_edges, presupposed, False,
        "STATED links grounded and CAUSAL-tagged; presupposed links surfaced as "
        "incomplete",
        report, prov)
