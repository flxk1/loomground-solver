# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Temporal construction (the TEMPORAL fact-dimension) — policy text → a
*grounded* temporal structure (procedural states + a state-machine of
transitions, strict before/after orderings, and anchored deadlines), or an
honest REJECT / ESCALATE. An [I]-tier op: the **model fills** the procedure, the
**contract gates** it, the harness **escalates** the open.

Sibling to :mod:`norm_construction`, :mod:`structural_construction` and
:mod:`causal_construction`. Where the structural op builds an ``is-a``/``part-of``
DAG and the causal op builds ``cause → effect`` links, this op extracts *when*:
the ordered procedure a policy text lays down — its steps/states, the transitions
between them (which **may legitimately loop** — an appeal sends a decided matter
back to review), the strict *sequence* constraints it imposes ("A before B"), and
the *deadlines* it sets ("within 30 days of filing"). It hands back a subgraph of
:class:`reasoning.Edge` all tagged :data:`dimensions.Dimension.TEMPORAL`, plus
deadlines expressed on the existing typed temporal primitives.

It wraps what exists rather than regrowing it:

  * the fill is the injected :data:`ports.ModelFn` (``str -> str``): the package
    never binds a model; the completion is a JSON proposal it decodes;
  * the reasoning is verified through :func:`interpret.interpret` (the fill seam,
    driven here by the decoded ordering relation) and :func:`interpret.audit`
    (the solver checking the ordering closes coherently) — the audit is *not*
    reimplemented;
  * the confidence floor is the existing contract:
    :func:`norm_contract.check_confidence` / :data:`norm_contract.CONFIDENCE_FLOOR`;
  * every deadline / duration is a **consumed** temporal primitive —
    :class:`temporal.RelativeDeadline` over a :class:`temporal.Duration`. This
    module never re-parses "30 days after filing" into home-grown arithmetic; it
    only *extracts* the anchor, offset and direction and hands them to the type
    layer that already validates them (the CONSUME-DON'T-REGROW discipline);
  * the output edge shape is the existing dimensioned :class:`reasoning.Edge`,
    every transition and every ordering tagged :data:`dimensions.Dimension.TEMPORAL`.

The temporal-honesty floor is committed, not optional:

  1. **grounding** — every state / transition / ordering / deadline span must be a
     *substring of the input text*. A span that is not found is REJECTED as
     invented. The harness never asserts an ungrounded step or deadline.
  2. **ordering-acyclicity** — the strict before/after **ordering** relation must
     be a DAG. A contradictory ordering (``A before B`` *and* ``B before A``) is a
     cycle → ESCALATE; a contradictory ordering is never returned. Note the scope:
     this applies to the ORDERING relation only. **State-machine transitions MAY
     loop** (appeal, remand, re-review) and are *not* checked for cycles — a
     looping transition is a normal procedure, not an error.
  3. **deadline-anchoring** — every deadline must anchor to an event/state that is
     *defined in the extracted structure*. A deadline whose anchor names no known
     state/event is FLAGGED (surfaced on ``flagged``) and the construction
     ESCALATES with the open anchor — you cannot resolve a deadline hung on
     nothing.
  4. **confidence is never trusted alone** — a high self-reported score cannot buy
     an acceptance past an unsound audit or an unanchored deadline; sub-floor
     confidence ESCALATES regardless.

Pure stdlib (``json``, ``dataclasses``, ``typing``). No governance, no corpus, no
domain: :func:`construct_temporal` takes a generic policy-text ``str`` — never a
corpus-coupled object. The solver is corpus-free; this op imports neither
``loomground_legal`` nor ``loomground_versum``.
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
from .temporal import Duration, RelativeDeadline, TemporalError

_DIRECTIONS = ("after", "before")


# ── the proposal schema the ModelFn returns ───────────────────────────────────

@dataclass(frozen=True)
class StateClaim:
    """One procedural state/step the text names, with its verbatim source span."""

    name: str
    span: str = ""
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "StateClaim":
        return cls(name=str(d.get("name", "")), span=str(d.get("span", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def well_formed(self) -> bool:
        return bool(self.name)


@dataclass(frozen=True)
class TransitionClaim:
    """One state-machine transition ``source →[label]→ target``. Transitions MAY
    loop (an appeal returns a decided matter to review); the ordering-acyclicity
    gate does *not* touch them."""

    source: str
    target: str
    label: str = ""
    span: str = ""
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "TransitionClaim":
        return cls(source=str(d.get("source", d.get("from", ""))),
                   target=str(d.get("target", d.get("to", ""))),
                   label=str(d.get("label", "")), span=str(d.get("span", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def well_formed(self) -> bool:
        return bool(self.source) and bool(self.target)

    def to_edge(self, source_pair: str) -> Edge:
        return Edge(
            subject=self.source,
            predicate=self.label or "transitions-to",
            object=self.target,
            dimension=Dimension.TEMPORAL,
            weight=max(0.0, min(1.0, self.confidence)),
            source_pair=source_pair,
        )


@dataclass(frozen=True)
class OrderingClaim:
    """One strict sequence constraint: ``before`` must precede ``after``. The set
    of these is the ORDERING relation the acyclicity gate checks for a DAG."""

    before: str
    after: str
    span: str = ""
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "OrderingClaim":
        return cls(before=str(d.get("before", "")), after=str(d.get("after", "")),
                   span=str(d.get("span", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def well_formed(self) -> bool:
        return bool(self.before) and bool(self.after)

    def to_edge(self, source_pair: str) -> Edge:
        return Edge(
            subject=self.before,
            predicate="before",
            object=self.after,
            dimension=Dimension.TEMPORAL,
            weight=max(0.0, min(1.0, self.confidence)),
            source_pair=source_pair,
        )


@dataclass(frozen=True)
class DeadlineClaim:
    """One deadline the text sets: an ``offset`` (an ISO 8601 duration string) in a
    ``direction`` (before/after) an ``anchor`` event/state, with a source span.
    The offset is validated by :class:`temporal.Duration`, not by this module."""

    anchor: str
    offset: str                          # ISO 8601 duration, e.g. "P30D"
    direction: str = "after"
    label: str = ""
    span: str = ""
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "DeadlineClaim":
        direction = str(d.get("direction", "after")).strip().lower()
        return cls(anchor=str(d.get("anchor", d.get("event", ""))),
                   offset=str(d.get("offset", d.get("duration", ""))),
                   direction=direction, label=str(d.get("label", "")),
                   span=str(d.get("span", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def parsed_offset(self) -> "Duration | None":
        """The offset as a consumed :class:`temporal.Duration`, or ``None`` if it
        does not parse — malformed, not guessed."""
        try:
            return Duration.parse(self.offset)
        except TemporalError:
            return None

    def well_formed(self) -> bool:
        return (bool(self.anchor) and self.direction in _DIRECTIONS
                and self.parsed_offset() is not None)

    def to_relative_deadline(self) -> RelativeDeadline:
        """CONSUME the temporal primitives: build a :class:`RelativeDeadline` over a
        :class:`Duration`. This module never reimplements deadline arithmetic."""
        return RelativeDeadline(event=self.anchor, offset=Duration.parse(self.offset),
                                direction=self.direction)


@dataclass(frozen=True)
class FlaggedDeadline:
    """A deadline whose anchor names no state/event in the extracted structure. It
    is surfaced, never resolved — you cannot hang a deadline on nothing."""

    anchor: str
    offset: str
    direction: str
    reason: str = "anchor is not a defined state/event in the extracted structure"

    def as_dict(self) -> dict[str, Any]:
        return {"anchor": self.anchor, "offset": self.offset,
                "direction": self.direction, "reason": self.reason}


@dataclass(frozen=True)
class TemporalProposal:
    """A model's proposed temporal structure. Convention, not truth — every claim
    is subject to the gates before any of it becomes a grounded Edge or deadline."""

    states: tuple[StateClaim, ...] = ()
    transitions: tuple[TransitionClaim, ...] = ()
    orderings: tuple[OrderingClaim, ...] = ()
    deadlines: tuple[DeadlineClaim, ...] = ()

    @classmethod
    def from_dict(cls, d: dict) -> "TemporalProposal":
        return cls(
            states=tuple(StateClaim.from_dict(s) for s in (d.get("states") or ())),
            transitions=tuple(
                TransitionClaim.from_dict(t) for t in (d.get("transitions") or ())),
            orderings=tuple(
                OrderingClaim.from_dict(o)
                for o in (d.get("orderings") or d.get("sequences") or ())),
            deadlines=tuple(
                DeadlineClaim.from_dict(dl) for dl in (d.get("deadlines") or ())),
        )

    @classmethod
    def from_json(cls, raw: str) -> "TemporalProposal":
        return cls.from_dict(json.loads(raw))

    def all_claims(self) -> tuple:
        return self.states + self.transitions + self.orderings + self.deadlines

    def defined_events(self) -> set[str]:
        """Every state/event *defined in the structure* — the anchors a deadline is
        allowed to reference: named states, transition endpoints, ordering ends."""
        events: set[str] = {s.name for s in self.states if s.name}
        for t in self.transitions:
            events.add(t.source)
            events.add(t.target)
        for o in self.orderings:
            events.add(o.before)
            events.add(o.after)
        events.discard("")
        return events


# ── the model port: a deterministic stub for tests ────────────────────────────

class StubModel:
    """A deterministic :data:`ports.ModelFn` (``str -> str``): it ignores the
    prompt and returns a *fixed* canned procedure as JSON. Faithful to the real
    seam — a host's model likewise returns a completion string that
    :func:`construct_temporal` decodes — but with no model runtime, so the gates
    are exercised deterministically. Construct with the proposal to propose::

        model = StubModel({"states": [...], "transitions": [...], ...})
    """

    def __init__(self, proposal: dict):
        self._payload = json.dumps(proposal)

    def __call__(self, prompt: str) -> str:   # ports.ModelFn
        return self._payload


def _build_prompt(text: str) -> str:
    """The instruction handed to the model. Content is irrelevant to the gates (a
    real model reads it; :class:`StubModel` ignores it) — but the call is a genuine
    ``ModelFn`` invocation, so the seam is consumed, not bypassed."""
    return (
        "Extract the temporal structure of the following policy text. Give the "
        "procedural states, the transitions between them (source, target, label — "
        "transitions may loop), the strict before/after orderings, and the "
        "deadlines (anchor event/state, ISO 8601 offset duration, direction). "
        "Supply the verbatim source SPAN and a confidence for each. Reply as "
        "JSON.\n\n" + text
    )


# ── the result ────────────────────────────────────────────────────────────────

@dataclass
class TemporalResult:
    """The outcome of a temporal-construction attempt. It carries the grounded
    temporal structure — states, TEMPORAL-tagged transition edges, TEMPORAL-tagged
    before/after ordering edges, and deadlines built on
    :class:`temporal.RelativeDeadline` — XOR a rejection / escalation. It never
    presents an ungrounded step, a contradictory ordering, or a deadline hung on
    an undefined anchor."""

    status: str                                  # extracted | rejected | escalated
    states: tuple[str, ...]
    transitions: tuple[Edge, ...]
    deadlines: tuple[RelativeDeadline, ...]
    sequences: tuple[Edge, ...]
    flagged: tuple[FlaggedDeadline, ...]
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


def _reject(reason, report, prov, flagged=()) -> TemporalResult:
    return TemporalResult("rejected", (), (), (), (), tuple(flagged), False,
                          reason, report, prov)


def _escalate(reason, report, prov, flagged=()) -> TemporalResult:
    return TemporalResult("escalated", (), (), (), (), tuple(flagged), True,
                          reason, report, prov)


# ── ordering-acyclicity (honesty floor #2) ────────────────────────────────────

def _find_cycle(orderings: tuple[OrderingClaim, ...]) -> list[str]:
    """Return a node cycle in the strict before→after ORDERING graph, or ``[]`` if
    it is a DAG. A contradictory ordering (``A before B`` and ``B before A``) is a
    two-node cycle. State-machine transitions are deliberately not passed here —
    they may loop. DFS: a back-edge onto a node on the current stack is a cycle."""
    adj: dict[str, list[str]] = {}
    for o in orderings:
        adj.setdefault(o.before, []).append(o.after)

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


# ── the reasoning-audit bridge (consumes interpret.interpret + interpret.audit)─

def _orderings_to_interp(orderings: tuple[OrderingClaim, ...]) -> dict:
    """Cast the strict orderings as facts + rules so the existing auditor can check
    the ordering relation closes coherently: the ``before`` event is a fact and the
    constraint is a rule ``before => after``. Reuses the solver's forward-chaining
    audit rather than reimplementing a soundness check."""
    facts: set[str] = set()
    rules: list[Rule] = []
    for i, o in enumerate(orderings):
        facts.add(o.before)
        rules.append(Rule(id=f"order:{i}", conditions=(o.before,),
                          consequence=o.after))
    return {"facts": facts, "rules": rules, "candidate": None}


def _audit_reasoning(text: str, orderings: tuple[OrderingClaim, ...]) -> dict:
    """Fill through :func:`interpret.interpret` (its ``parse`` seam driven by the
    decoded orderings) then verify with :func:`interpret.audit`."""
    interp = _interpret(text, parse=lambda _t: _orderings_to_interp(orderings))
    return _audit_interp(interp)


# ── the norm-contract bridge (consumes the existing confidence gate) ──────────

def _confidence_finding(min_conf: float, risk_class: str):
    """NT-9 via :func:`norm_contract.check_confidence`."""
    pair = {"id": "temporal", "solution": {"confidence": min_conf}}
    return norm_contract.check_confidence(pair, risk_class=risk_class)


def _has_escalate(findings) -> bool:
    return any(f.level is Level.ESCALATE for f in findings)


# ── grounding helpers (honesty floor #1) ──────────────────────────────────────

def _span_of(claim) -> str:
    return getattr(claim, "span", "")


def _receipt(claim, text: str) -> dict[str, Any]:
    span = _span_of(claim)
    start = text.find(span) if span else -1
    return {"kind": type(claim).__name__, "span": span, "start": start,
            "end": start + len(span) if start >= 0 else -1,
            "grounded": start >= 0}


# ── the op ────────────────────────────────────────────────────────────────────

def construct_temporal(
    text: str,
    *,
    model: ModelFn,
    risk_class: str = "C",
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> TemporalResult:
    """Construct a grounded temporal structure from ``text``, or reject / escalate.

    The ``model`` (an injected :data:`ports.ModelFn`) proposes a procedure;
    deterministic gates over ``(proposal, text)`` then decide. The gates, in order
    of precedence:

      * **well-formedness** — a state with no name, a transition missing an
        endpoint, an ordering missing a side, or a deadline with no anchor / a
        bad direction / an unparseable ISO offset is malformed → REJECT;
      * **grounding** (floor #1) — any state / transition / ordering / deadline
        whose span is not a substring of ``text`` is invented → REJECT (no edge,
        no deadline is returned);
      * **ordering-acyclicity** (floor #2) — a cycle in the strict before/after
        ORDERING relation (including a contradictory ``A before B`` + ``B before
        A``) → ESCALATE. State-machine transitions are exempt: they MAY loop;
      * **deadline-anchoring** (floor #3) — a deadline whose anchor is not a state/
        event defined in the extracted structure is FLAGGED and the construction
        ESCALATES with the open anchor surfaced on ``flagged``;
      * **audit** — :func:`interpret.audit` must find the ordering relation sound;
      * **confidence floor** — NT-9 / :data:`CONFIDENCE_FLOOR` over every claim;
        sub-floor → ESCALATE, regardless of any high self-reported score.

    Only a proposal that is well-formed, grounded, has an acyclic ordering, hangs
    every deadline on a defined anchor, audits sound and sits at/above the floor is
    EXTRACTED — with transitions and orderings returned as
    :data:`Dimension.TEMPORAL`-tagged :class:`reasoning.Edge`, and deadlines as
    :class:`temporal.RelativeDeadline` over :class:`temporal.Duration`. Escalation
    is a pass.
    """
    prov: dict[str, Any] = {"receipts": []}
    report: dict[str, Any] = {}

    # 0. Fill: consume the ModelFn seam and decode the proposal.
    raw = model(_build_prompt(text))
    try:
        proposal = TemporalProposal.from_json(raw) if isinstance(raw, str) \
            else TemporalProposal.from_dict(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        report["decode"] = {"ok": False, "error": str(exc)}
        return _reject("model returned an undecodable proposal", report, prov)

    prov["receipts"] = [_receipt(c, text) for c in proposal.all_claims()]

    # 1. Well-formedness of every proposed claim.
    malformed = [type(c).__name__ for c in proposal.all_claims() if not c.well_formed()]
    report["wellformed"] = {"ok": not malformed, "malformed": malformed}
    if malformed:
        return _reject(
            f"malformed temporal claim(s) — missing field, bad direction, or "
            f"unparseable offset: {malformed!r}", report, prov)

    # 2. Grounding (honesty floor #1): reject any invented span.
    invented = [_span_of(c) for c in proposal.all_claims()
                if not (_span_of(c) and _span_of(c) in text)]
    report["grounding"] = {"ok": not invented, "invented": invented}
    if invented:
        return _reject(
            f"ungrounded temporal claim(s) — span not found in text: {invented!r}",
            report, prov)

    # 3. Ordering-acyclicity (honesty floor #2): a cycle in the strict before/after
    #    ordering is a contradiction → escalate. Transitions are NOT checked here;
    #    a looping transition (appeal, remand) is a normal procedure.
    cycle = _find_cycle(proposal.orderings)
    report["acyclicity"] = {"ok": not cycle, "cycle": cycle,
                            "transitions_exempt": len(proposal.transitions)}
    if cycle:
        return _escalate(
            "contradictory ordering — the strict before/after relation is not a "
            "DAG: " + " -> ".join(cycle), report, prov)

    # 4. Deadline-anchoring (honesty floor #3): every deadline must anchor to a
    #    state/event defined in the structure. An unanchored deadline is flagged
    #    and the construction escalates with the open anchor.
    defined = proposal.defined_events()
    flagged = tuple(
        FlaggedDeadline(anchor=dl.anchor, offset=dl.offset, direction=dl.direction)
        for dl in proposal.deadlines if dl.anchor not in defined
    )
    report["anchoring"] = {"ok": not flagged, "defined_events": sorted(defined),
                           "flagged": [f.as_dict() for f in flagged]}
    if flagged:
        return _escalate(
            "unanchored deadline(s) — anchor names no defined state/event: "
            + ", ".join(f"{f.offset} {f.direction} {f.anchor!r}" for f in flagged),
            report, prov, flagged=flagged)

    # 5. Audit: consume interpret.interpret + interpret.audit over the ordering
    #    relation. Confidence is never trusted alone — an unsound ordering escalates
    #    no matter how high the self-reported score.
    audit_report = _audit_reasoning(text, proposal.orderings)
    audited = audit_report["verdict"] == "sound"
    report["audit"] = {"verdict": audit_report["verdict"],
                       "reasons": audit_report["reasons"]}
    if not audited:
        return _escalate(
            "audit unsound — " + "; ".join(audit_report["reasons"]), report, prov)

    # 6. Confidence floor: NT-9 plus a hard floor independent of risk_class, over
    #    every grounded claim.
    confs = [c.confidence for c in proposal.all_claims()]
    min_conf = min(confs) if confs else 0.0
    nt9 = _confidence_finding(min_conf, risk_class)
    sub_floor = min_conf < confidence_floor or _has_escalate(nt9)
    report["confidence"] = {"min": min_conf, "floor": confidence_floor,
                            "ok": not sub_floor,
                            "nt9": [f.to_dict() for f in nt9]}
    if sub_floor:
        return _escalate(
            f"sub-floor confidence {min_conf} < {confidence_floor}", report, prov)

    # 7. Extract — well-formed, grounded, acyclic ordering, anchored deadlines,
    #    audited sound, at/above the floor. Build the TEMPORAL-tagged subgraph and
    #    the deadlines on the consumed temporal primitives.
    states = tuple(dict.fromkeys(s.name for s in proposal.states))
    transitions = tuple(t.to_edge(f"temporal:transition:{i}")
                        for i, t in enumerate(proposal.transitions))
    sequences = tuple(o.to_edge(f"temporal:order:{i}")
                      for i, o in enumerate(proposal.orderings))
    deadlines = tuple(dl.to_relative_deadline() for dl in proposal.deadlines)

    # Belt-and-suspenders invariants.
    assert all(e.dimension is Dimension.TEMPORAL for e in transitions + sequences), \
        "invariant: a grounded temporal edge is not TEMPORAL-tagged"
    assert all(isinstance(d, RelativeDeadline) and isinstance(d.offset, Duration)
               for d in deadlines), \
        "invariant: a deadline is not built on temporal.RelativeDeadline/Duration"

    report["extracted"] = {"states": len(states), "transitions": len(transitions),
                           "orderings": len(sequences), "deadlines": len(deadlines)}
    return TemporalResult(
        "extracted", states, transitions, deadlines, sequences, (), False,
        "grounded, acyclic ordering, anchored deadlines, audited sound and at/"
        "above the floor; transitions and orderings TEMPORAL-tagged, deadlines on "
        "temporal.RelativeDeadline/Duration",
        report, prov)
