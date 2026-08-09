# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Structural construction (the STRUCTURAL fact-dimension) — policy text → a
*grounded* ontology (concepts + is-a/part-of edges + definitions), or an honest
REJECT / ESCALATE. An [I]-tier op: the **model fills** the ontology, the
**contract gates** it, the harness **escalates** the open.

Sibling to :mod:`norm_construction`. Where that op builds one
:class:`subsumption.Rule` from a norm-text, this one builds the *structural*
subgraph a policy text implies — the entity/term types it names, how they nest
(``is-a`` / ``part-of``) and how its terms are defined — and hands back a
subgraph of :class:`reasoning.Edge` all tagged :data:`dimensions.Dimension.STRUCTURAL`.
It is deliberately not a decider: a model proposes concepts, hierarchy edges and
definitions, **each tagged with the source span it was drawn from** and a
confidence, and then a chain of **deterministic gates** decides whether that
proposal may become a subgraph at all.

It wraps what exists rather than regrowing it:

  * the fill is the injected :data:`ports.ModelFn` (``str -> str``): the package
    never binds a model; the completion is a JSON proposal it decodes;
  * the reasoning is verified through :func:`interpret.interpret` (the fill seam,
    driven here by the decoded proposal) and :func:`interpret.audit` (the solver
    catching a self-contradictory hierarchy) — the audit is *not* reimplemented;
  * the confidence floor is the existing contract:
    :func:`norm_contract.check_confidence` / :data:`norm_contract.CONFIDENCE_FLOOR`;
  * the output edge shape is the existing dimensioned :class:`reasoning.Edge`,
    every one tagged :data:`dimensions.Dimension.STRUCTURAL`.

The structural-honesty floor is committed, not optional:

  1. **grounding** — every concept / edge / definition span must be a *substring
     of the input text*. A span not found is REJECTED as invented. The harness
     never returns an ungrounded concept.
  2. **acyclic hierarchy** — the ``is-a`` / ``part-of`` graph must be a DAG. A
     cycle is a broken ontology → ESCALATE; a cyclic hierarchy is never returned.
  3. **definition-closure** — every term *used* (a hierarchy endpoint, or a term
     a definition draws on) must resolve to a declared concept, to a definition
     in the subgraph, or be explicitly marked external/primitive. An undefined,
     unmarked term is FLAGGED and the construction escalates with the open terms.
  4. **confidence is never trusted alone** — a high self-reported score cannot
     buy an acceptance past a cyclic hierarchy, an open term or an unsound audit;
     and a sub-floor score escalates regardless of the score on any one element.

Pure stdlib (``json``, ``dataclasses``, ``typing``). No governance, no
corpus, no domain: :func:`construct_structure` takes a generic policy-text
``str`` — never a corpus-coupled object. The solver is corpus-free and does not
reach into Versum; a downstream bridge persists the subgraph, not this module.
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


# ── the hierarchy predicates this op recognises ───────────────────────────────
# Only the two *structural* nesting relations. Anything else a model proposes as
# a hierarchy predicate is normalised to nothing and the edge is malformed.
_ISA = "is-a"
_PARTOF = "part-of"
_HIERARCHY_PREDICATES = frozenset({_ISA, _PARTOF})


def _norm_predicate(p: str) -> str:
    """Normalise a proposed hierarchy predicate to ``is-a`` / ``part-of`` / ''."""
    n = (p or "").strip().lower().replace("_", "-").replace(" ", "-")
    if n in {"is-a", "isa", "kind-of", "subclass", "subclass-of", "instance-of"}:
        return _ISA
    if n in {"part-of", "partof", "has-part", "component-of", "contains", "composed-of"}:
        return _PARTOF
    return ""


# ── the proposal schema the ModelFn returns ───────────────────────────────────

@dataclass(frozen=True)
class Concept:
    """One proposed entity/term type: the ``name`` the solver reasons over, the
    verbatim ``span`` it was drawn from, and the model's confidence in it."""

    span: str
    name: str
    confidence: float = 1.0
    kind: str = "concept"       # concept | entity | term (free label, not gated)

    @classmethod
    def from_dict(cls, d: dict) -> "Concept":
        return cls(span=str(d.get("span", "")),
                   name=str(d.get("name", "")),
                   confidence=float(d.get("confidence", 1.0)),
                   kind=str(d.get("kind", "concept")))

    def grounded_in(self, text: str) -> bool:
        return bool(self.span) and self.span in text


@dataclass(frozen=True)
class HierarchyEdge:
    """A proposed ``is-a`` / ``part-of`` edge between two concept names, the span
    it was drawn from and a confidence. Cast to a :class:`reasoning.Edge` tagged
    :data:`dimensions.Dimension.STRUCTURAL` only if the whole proposal is
    accepted."""

    span: str
    subject: str
    predicate: str              # normalised: is-a | part-of
    object: str
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "HierarchyEdge":
        return cls(span=str(d.get("span", "")),
                   subject=str(d.get("subject", "")),
                   predicate=_norm_predicate(str(d.get("predicate", ""))),
                   object=str(d.get("object", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def grounded_in(self, text: str) -> bool:
        return bool(self.span) and self.span in text

    def to_edge(self) -> Edge:
        """The dimensioned STRUCTURAL edge this proposal becomes when accepted."""
        return Edge(
            subject=self.subject,
            predicate=self.predicate,
            object=self.object,
            dimension=Dimension.STRUCTURAL,
            weight=max(0.0, min(1.0, self.confidence)),
            source_pair="structural_construction",
        )


@dataclass(frozen=True)
class Definition:
    """A proposed definition: the ``term`` defined, the verbatim definition
    ``text``/span it was drawn from, the constituent terms it ``uses``, a
    confidence, and whether the defined term is itself a ``primitive`` (external —
    it needs no further breakdown)."""

    span: str
    term: str
    uses: tuple[str, ...] = ()
    confidence: float = 1.0
    primitive: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "Definition":
        return cls(span=str(d.get("span", "")),
                   term=str(d.get("term", "")),
                   uses=tuple(str(u) for u in (d.get("uses") or ())),
                   confidence=float(d.get("confidence", 1.0)),
                   primitive=bool(d.get("primitive", False)
                                  or d.get("external", False)))

    def grounded_in(self, text: str) -> bool:
        return bool(self.span) and self.span in text


@dataclass(frozen=True)
class StructuralProposal:
    """A model's proposed ontology of a policy text. Convention, not truth —
    every field is subject to the gates before any of it becomes a subgraph."""

    concepts: tuple[Concept, ...] = ()
    edges: tuple[HierarchyEdge, ...] = ()
    definitions: tuple[Definition, ...] = ()
    external: tuple[str, ...] = ()          # terms declared external/primitive

    @classmethod
    def from_dict(cls, d: dict) -> "StructuralProposal":
        return cls(
            concepts=tuple(Concept.from_dict(c) for c in (d.get("concepts") or ())),
            edges=tuple(HierarchyEdge.from_dict(e) for e in (d.get("edges") or ())),
            definitions=tuple(Definition.from_dict(x)
                              for x in (d.get("definitions") or ())),
            external=tuple(str(t) for t in (d.get("external") or ())),
        )

    @classmethod
    def from_json(cls, raw: str) -> "StructuralProposal":
        return cls.from_dict(json.loads(raw))

    def min_confidence(self) -> float:
        confs = [c.confidence for c in self.concepts]
        confs += [e.confidence for e in self.edges]
        confs += [d.confidence for d in self.definitions]
        return min(confs) if confs else 0.0


# ── the model port: a deterministic stub for tests ────────────────────────────

class StubModel:
    """A deterministic :data:`ports.ModelFn` (``str -> str``): it ignores the
    prompt and returns a *fixed* canned ontology as JSON. Faithful to the real
    seam — a host's model likewise returns a completion string that
    :func:`construct_structure` decodes — but with no model runtime, so the gates
    are exercised deterministically. Construct with the proposal you want::

        model = StubModel({"concepts": [...], "edges": [...], "definitions": [...]})
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
        "Extract the ontology of the following policy text: the concepts "
        "(entity/term types) it names, the is-a and part-of edges between them, "
        "and the definitions of its terms. For every concept, edge and "
        "definition return the verbatim source SPAN, a solver name/literal and a "
        "confidence; mark any external/primitive term. Reply as JSON.\n\n" + text
    )


# ── the result ────────────────────────────────────────────────────────────────

@dataclass
class StructuralResult:
    """The outcome of a construction attempt. It carries a grounded structural
    subgraph XOR a rejection/escalation — never an ungrounded concept and never a
    cyclic hierarchy."""

    status: str                                  # extracted | rejected | escalated
    concepts: tuple[Concept, ...]
    edges: tuple[Edge, ...]                      # dimensioned STRUCTURAL edges
    definitions: tuple[Definition, ...]
    flagged: tuple[str, ...]                     # undefined, unmarked terms
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


def _reject(reason: str, report: dict, prov: dict) -> StructuralResult:
    return StructuralResult("rejected", (), (), (), (), False, reason, report, prov)


def _escalate(reason: str, report: dict, prov: dict,
              *, flagged: tuple[str, ...] = ()) -> StructuralResult:
    return StructuralResult("escalated", (), (), (), flagged, True,
                            reason, report, prov)


# ── provenance receipts ───────────────────────────────────────────────────────

def _receipt(text: str, *, role: str, span: str, name: str,
             confidence: float) -> dict[str, Any]:
    start = text.find(span) if span else -1
    end = start + len(span) if start >= 0 else -1
    return {"role": role, "name": name, "span": span, "start": start,
            "end": end, "confidence": confidence, "grounded": start >= 0}


def _all_receipts(text: str, proposal: StructuralProposal) -> list[dict[str, Any]]:
    out = [_receipt(text, role="concept", span=c.span, name=c.name,
                    confidence=c.confidence) for c in proposal.concepts]
    out += [_receipt(text, role=f"edge:{e.predicate or '?'}", span=e.span,
                     name=f"{e.subject} {e.predicate} {e.object}",
                     confidence=e.confidence) for e in proposal.edges]
    out += [_receipt(text, role="definition", span=d.span, name=d.term,
                     confidence=d.confidence) for d in proposal.definitions]
    return out


# ── acyclicity (honesty floor #2) ─────────────────────────────────────────────

def _find_cycle(edges: tuple[HierarchyEdge, ...]) -> list[str]:
    """Return a node cycle in the ``is-a``/``part-of`` graph, or ``[]`` if a DAG.

    Directed edge ``subject → object``. A back-edge onto a node on the current
    DFS stack is a cycle; the returned list is the stack slice that closes it."""
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e.subject, []).append(e.object)

    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str]:
        colour[node] = GREY
        stack.append(node)
        for nxt in adj.get(node, ()):
            c = colour.get(nxt, WHITE)
            if c == GREY:                       # back-edge → cycle
                i = stack.index(nxt)
                return stack[i:] + [nxt]
            if c == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        colour[node] = BLACK
        return []

    for n in list(adj.keys()):
        if colour.get(n, WHITE) == WHITE:
            cyc = visit(n)
            if cyc:
                return cyc
    return []


# ── definition-closure (honesty floor #3) ─────────────────────────────────────

def _undefined_terms(proposal: StructuralProposal) -> list[str]:
    """The terms *used* that resolve to no definition, no declared concept, and
    are not marked external/primitive. These are the open terms of the ontology."""
    known = {c.name for c in proposal.concepts if c.name}
    known |= {d.term for d in proposal.definitions if d.term}
    known |= {t for t in proposal.external}
    known |= {d.term for d in proposal.definitions if d.primitive}

    used: set[str] = set()
    for e in proposal.edges:
        if e.subject:
            used.add(e.subject)
        if e.object:
            used.add(e.object)
    for d in proposal.definitions:
        used |= {u for u in d.uses if u}

    return sorted(used - known)


# ── the reasoning-audit bridge (consumes interpret.interpret + interpret.audit)─

def _proposal_to_interp(proposal: StructuralProposal) -> dict:
    """Cast the hierarchy as facts + subsumption rules so the existing auditor can
    check it: each concept name is a fact, each ``is-a``/``part-of`` edge is a
    rule ``subject => object`` (nesting entails the parent), and there is no
    single candidate. A hierarchy that forces a concept and its negation into the
    closure then comes back inconsistent — the solver catching a broken
    decomposition — without this module reimplementing the audit."""
    facts = {c.name for c in proposal.concepts if c.name}
    rules = [
        Rule(id=f"h{i}", conditions=(e.subject,), consequence=e.object)
        for i, e in enumerate(proposal.edges)
        if e.subject and e.object
    ]
    facts |= {e.subject for e in proposal.edges if e.subject}
    return {"facts": facts, "rules": rules, "candidate": None}


def _audit_reasoning(text: str, proposal: StructuralProposal) -> dict:
    """Fill through :func:`interpret.interpret` (its ``parse`` seam driven by the
    decoded proposal) then verify with :func:`interpret.audit`."""
    interp = _interpret(text, parse=lambda _t: _proposal_to_interp(proposal))
    return _audit_interp(interp)


# ── the norm-contract confidence bridge (consumes the existing gate) ──────────

def _confidence_finding(min_conf: float, risk_class: str):
    """The confidence floor via :func:`norm_contract.check_confidence`."""
    pair = {"id": "structural", "solution": {"confidence": min_conf}}
    return norm_contract.check_confidence(pair, risk_class=risk_class)


def _has_escalate(findings) -> bool:
    return any(f.level is Level.ESCALATE for f in findings)


# ── the op ────────────────────────────────────────────────────────────────────

def construct_structure(
    text: str,
    *,
    model: ModelFn,
    risk_class: str = "C",
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> StructuralResult:
    """Construct a grounded structural subgraph from ``text``, or reject/escalate.

    The ``model`` (an injected :data:`ports.ModelFn`) proposes an ontology —
    concepts, ``is-a``/``part-of`` edges and definitions, each span-tagged with a
    confidence; deterministic gates over ``(proposal, text)`` then decide. In
    order of precedence:

      * **grounding** — any concept/edge/definition span not a substring of
        ``text`` is invented → REJECT (no subgraph);
      * **well-formedness** — a proposal with no concepts, or a hierarchy edge
        whose predicate is neither ``is-a`` nor ``part-of``, is malformed →
        REJECT;
      * **acyclicity** — a cycle in the ``is-a``/``part-of`` graph is a broken
        ontology → ESCALATE (a cyclic hierarchy is never returned);
      * **definition-closure** — a term used but neither defined, declared, nor
        marked external/primitive is an open term → FLAG and ESCALATE, carrying
        the open terms in :attr:`StructuralResult.flagged`;
      * **audit** — :func:`interpret.audit` must find the hierarchy sound; an
        inconsistent decomposition → ESCALATE regardless of confidence;
      * **confidence floor** — :func:`norm_contract.check_confidence` /
        :data:`CONFIDENCE_FLOOR`; sub-floor → ESCALATE, regardless of any single
        high score.

    Only a proposal that is grounded AND acyclic AND closed AND audited AND
    at/above the floor is EXTRACTED, and only then is a subgraph returned — a
    tuple of :class:`reasoning.Edge` every one tagged
    :data:`dimensions.Dimension.STRUCTURAL`.
    """
    prov: dict[str, Any] = {"text_len": len(text), "receipts": []}
    report: dict[str, Any] = {}

    # 0. Fill: consume the ModelFn seam and decode the proposal.
    raw = model(_build_prompt(text))
    try:
        proposal = StructuralProposal.from_json(raw) if isinstance(raw, str) \
            else StructuralProposal.from_dict(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        report["decode"] = {"ok": False, "error": str(exc)}
        return _reject("model returned an undecodable proposal", report, prov)

    prov["receipts"] = _all_receipts(text, proposal)

    # 1. Grounding (honesty floor #1): reject any invented span.
    invented: list[str] = []
    invented += [c.span for c in proposal.concepts if not c.grounded_in(text)]
    invented += [e.span for e in proposal.edges if not e.grounded_in(text)]
    invented += [d.span for d in proposal.definitions if not d.grounded_in(text)]
    report["grounding"] = {"ok": not invented, "invented": invented}
    if invented:
        return _reject(
            f"ungrounded element(s) — span not found in text: {invented!r}",
            report, prov)

    # 2. Well-formedness: at least one concept, and every hierarchy predicate
    #    resolved to is-a / part-of.
    bad_predicates = [
        f"{e.subject} {e.object}" for e in proposal.edges
        if e.predicate not in _HIERARCHY_PREDICATES or not (e.subject and e.object)
    ]
    wf_ok = bool(proposal.concepts) and not bad_predicates
    report["wellformed"] = {
        "ok": wf_ok,
        "reason": ("" if wf_ok else
                   ("no concepts proposed" if not proposal.concepts
                    else f"non-hierarchy or malformed edge(s): {bad_predicates!r}")),
    }
    if not wf_ok:
        return _reject("malformed proposal: " + report["wellformed"]["reason"],
                       report, prov)

    # 3. Acyclicity (honesty floor #2): a cycle in the hierarchy → escalate.
    cycle = _find_cycle(proposal.edges)
    report["acyclicity"] = {"ok": not cycle, "cycle": cycle}
    if cycle:
        return _escalate(
            "cyclic hierarchy — the is-a/part-of graph is not a DAG: "
            + " -> ".join(cycle), report, prov)

    # 4. Definition-closure (honesty floor #3): open terms → flag + escalate.
    flagged = tuple(_undefined_terms(proposal))
    report["closure"] = {"ok": not flagged, "undefined": list(flagged)}
    if flagged:
        return _escalate(
            "definition-closure flag — term(s) used but undefined and unmarked: "
            + repr(list(flagged)),
            report, prov, flagged=flagged)

    # 5. Audit: consume interpret.interpret + interpret.audit.
    audit_report = _audit_reasoning(text, proposal)
    audited = audit_report["verdict"] == "sound"
    report["audit"] = {"verdict": audit_report["verdict"],
                       "reasons": audit_report["reasons"]}
    if not audited:
        # Confidence is never trusted alone: an unsound hierarchy escalates no
        # matter how high the self-reported score.
        return _escalate("audit unsound — " + "; ".join(audit_report["reasons"]),
                         report, prov)

    # 6. Confidence floor: NT-9 plus a hard floor independent of risk_class.
    min_conf = proposal.min_confidence()
    nt9 = _confidence_finding(min_conf, risk_class)
    sub_floor = min_conf < confidence_floor or _has_escalate(nt9)
    report["confidence"] = {"min": min_conf, "floor": confidence_floor,
                            "ok": not sub_floor,
                            "nt9": [f.to_dict() for f in nt9]}
    if sub_floor:
        return _escalate(
            f"sub-floor confidence {min_conf} < {confidence_floor}", report, prov)

    # 7. Extract — grounded, acyclic, closed, audited, at/above the floor.
    edges = tuple(e.to_edge() for e in proposal.edges)
    # Belt-and-suspenders: never hand back an ungrounded concept, and every
    # returned edge carries the STRUCTURAL dimension.
    assert all(r["grounded"] for r in prov["receipts"]), \
        "invariant: extracted subgraph has an ungrounded receipt"
    assert all(e.dimension is Dimension.STRUCTURAL for e in edges), \
        "invariant: a returned structural edge is not tagged STRUCTURAL"
    report["extracted"] = True
    return StructuralResult(
        "extracted", proposal.concepts, edges, proposal.definitions, (),
        False, "grounded, acyclic, closed, audited and at/above the floor",
        report, prov)
