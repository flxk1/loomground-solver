# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Relational construction (the RELATIONAL fact-dimension) — policy text → a
*grounded* relation graph (typed parties + relation edges + jural positions), or
an honest REJECT / ESCALATE. An [I]-tier op: the **model fills** the graph, the
**contract gates** it, the harness **escalates** the open.

Sibling to :mod:`structural_construction` (the ontology op) and
:mod:`causal_construction`. Where the structural op builds the ``is-a``/
``part-of`` nesting of a policy text, this one builds the *relational* subgraph:
the roles it names (typed parties — controller/processor/data-subject,
provider/deployer/user, employer/employee, …), the relation edges between them
(``acts-for``, ``provides-to``, ``employs``, ``owns``, ``member-of``, …), and the
Hohfeldian jural positions it asserts (a role bearing a claim/privilege/power/
immunity toward a counterparty). It hands back a subgraph of
:class:`reasoning.Edge` every one tagged
:data:`dimensions.Dimension.RELATIONAL` — or rejects/escalates.

It **consumes** what the solver already has rather than regrowing it:

  * the fill is the injected :data:`ports.ModelFn` (``str -> str``): the package
    never binds a model; the completion is a JSON proposal it decodes;
  * **relation composition** is :class:`relation.RelationAlgebra` — its
    :meth:`~relation.RelationAlgebra.compose_path` folds a stated relation chain,
    and its :data:`relation.ESCALATE` sentinel is the escalate-don't-guess marker
    for a *contested* chain. This module never reimplements composition;
  * **Hohfeld correlativity** is :func:`deontic.incidents.correlative` (with
    :func:`~deontic.incidents.is_advantage` and the fixed
    :data:`~deontic.incidents.INCIDENTS` vocabulary): the counterparty position a
    jural advantage entails. This module never reimplements the correlative
    table;
  * the reasoning is verified through :func:`interpret.interpret` (the fill seam,
    driven by the decoded proposal) and :func:`interpret.audit` (the solver
    catching a self-contradictory relation set) — the audit is *not*
    reimplemented;
  * the confidence floor is the existing contract
    :func:`norm_contract.check_confidence` / :data:`norm_contract.CONFIDENCE_FLOOR`;
  * the output edge shape is the dimensioned :class:`reasoning.Edge`, every one
    tagged :data:`dimensions.Dimension.RELATIONAL`.

The relational-honesty floor is committed, not optional:

  1. **grounding** — every role / relation / jural-position span must be a
     *substring of the input text*. A span not found is REJECTED as invented.
  2. **correlativity-consistency** — every stated jural *advantage* (claim /
     privilege / power / immunity) must name a counterparty that bears its
     :func:`deontic.incidents.correlative` position; a right asserted with **no
     correlative counterparty** is FLAGGED and the construction escalates with
     the open rights.
  3. **composability** — a stated relation chain must compose via
     :meth:`relation.RelationAlgebra.compose_path`; a chain that folds to the
     :data:`relation.ESCALATE` sentinel is *contested* → ESCALATE, never a
     fabricated composite.
  4. **confidence is never trusted alone** — a high self-reported score cannot
     buy an acceptance past a missing correlative, a contested chain or an
     unsound audit; and a sub-floor score escalates regardless of any single
     high score.

Pure stdlib (``json``, ``dataclasses``, ``typing``) plus the in-tree ``deontic``
package the solver already depends on. No governance, no corpus, no legal
plane: :func:`construct_relational` takes a generic policy-text ``str`` — never a
corpus-coupled object, and it imports neither ``loomground_legal`` nor
``loomground_versum``. A downstream bridge persists the subgraph, not this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Hashable

from deontic.incidents import INCIDENTS, correlative, is_advantage

from . import norm_contract
from .dimensions import Dimension
from .interpret import audit as _audit_interp
from .interpret import interpret as _interpret
from .norm_contract import CONFIDENCE_FLOOR, Level
from .ports import ModelFn
from .reasoning import Edge
from .relation import ESCALATE, RelationAlgebra
from .subsumption import Rule

_INCIDENTS = frozenset(INCIDENTS)


def _norm_token(t: str) -> str:
    """Canonicalise a relation predicate / role token (lower, hyphen-joined)."""
    return (t or "").strip().lower().replace("_", "-").replace(" ", "-")


# ── the proposal schema the ModelFn returns ───────────────────────────────────

@dataclass(frozen=True)
class Role:
    """One proposed typed party: the ``name`` the solver reasons over, an
    optional ``kind`` (controller/processor/provider/… — a free label, not
    gated), the verbatim ``span`` it was drawn from, and a confidence."""

    span: str
    name: str
    kind: str = "party"
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "Role":
        return cls(span=str(d.get("span", "")),
                   name=str(d.get("name", "")),
                   kind=str(d.get("kind", "party")),
                   confidence=float(d.get("confidence", 1.0)))

    def grounded_in(self, text: str) -> bool:
        return bool(self.span) and self.span in text


@dataclass(frozen=True)
class RelationEdge:
    """A proposed relation between two role names — ``subject`` ``predicate``
    ``object`` (e.g. ``processor acts-for controller``) — the span it was drawn
    from and a confidence. Cast to a :class:`reasoning.Edge` tagged
    :data:`dimensions.Dimension.RELATIONAL` only if the whole proposal is
    accepted."""

    span: str
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "RelationEdge":
        return cls(span=str(d.get("span", "")),
                   subject=str(d.get("subject", "")),
                   predicate=_norm_token(str(d.get("predicate", ""))),
                   object=str(d.get("object", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def grounded_in(self, text: str) -> bool:
        return bool(self.span) and self.span in text

    def to_edge(self) -> Edge:
        """The dimensioned RELATIONAL edge this proposal becomes when accepted."""
        return Edge(
            subject=self.subject,
            predicate=self.predicate,
            object=self.object,
            dimension=Dimension.RELATIONAL,
            weight=max(0.0, min(1.0, self.confidence)),
            source_pair="relational_construction",
        )


@dataclass(frozen=True)
class JuralPosition:
    """A proposed Hohfeldian position a role bears toward a counterparty: the
    ``holder`` role, one of the eight :data:`deontic.incidents.INCIDENTS`, the
    ``counterparty`` role (may be empty — that is exactly the FLAG the
    correlativity gate catches), the span it was drawn from and a confidence."""

    span: str
    holder: str
    incident: str
    counterparty: str = ""
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "JuralPosition":
        return cls(span=str(d.get("span", "")),
                   holder=str(d.get("holder", "")),
                   incident=_norm_token(str(d.get("incident", ""))),
                   counterparty=str(d.get("counterparty", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def grounded_in(self, text: str) -> bool:
        return bool(self.span) and self.span in text


@dataclass(frozen=True)
class CorrelativePosition:
    """A counterparty position *derived* (not proposed) from a stated advantage
    via :func:`deontic.incidents.correlative`: the ``role`` that bears it, the
    correlative ``incident`` (e.g. a claim's ``duty``), and the ``toward`` holder
    whose advantage entails it."""

    role: str
    incident: str            # the deontic.correlative of the advantage
    toward: str              # the advantage-holder role
    source_incident: str     # the advantage that entails it

    def as_dict(self) -> dict[str, Any]:
        return {"role": self.role, "incident": self.incident,
                "toward": self.toward, "source_incident": self.source_incident}


@dataclass(frozen=True)
class RelationalProposal:
    """A model's proposed relation graph of a policy text. Convention, not truth
    — every field is subject to the gates before any of it becomes a subgraph.

    ``composition`` is the (partial) two-step composition table the relation
    algebra is built from: a list of ``{"a", "b", "result"}`` rows, where
    ``result`` is a relation predicate or the string ``"ESCALATE"`` marking a
    *contested* chain. ``chains`` are the stated relation chains (lists of
    predicates) to be folded through :meth:`relation.RelationAlgebra.compose_path`.
    ``inverses`` is an optional dual-relation map."""

    roles: tuple[Role, ...] = ()
    relations: tuple[RelationEdge, ...] = ()
    jural: tuple[JuralPosition, ...] = ()
    composition: tuple[dict[str, str], ...] = ()
    chains: tuple[tuple[str, ...], ...] = ()
    inverses: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "RelationalProposal":
        return cls(
            roles=tuple(Role.from_dict(r) for r in (d.get("roles") or ())),
            relations=tuple(RelationEdge.from_dict(e)
                            for e in (d.get("relations") or ())),
            jural=tuple(JuralPosition.from_dict(j) for j in (d.get("jural") or ())),
            composition=tuple(
                {"a": _norm_token(str(c.get("a", ""))),
                 "b": _norm_token(str(c.get("b", ""))),
                 "result": (str(c.get("result", "")).strip()
                            if str(c.get("result", "")).strip().upper() == "ESCALATE"
                            else _norm_token(str(c.get("result", ""))))}
                for c in (d.get("composition") or ())),
            chains=tuple(tuple(_norm_token(str(p)) for p in chain)
                         for chain in (d.get("chains") or ())),
            inverses={_norm_token(str(k)): _norm_token(str(v))
                      for k, v in (d.get("inverses") or {}).items()},
        )

    @classmethod
    def from_json(cls, raw: str) -> "RelationalProposal":
        return cls.from_dict(json.loads(raw))

    def min_confidence(self) -> float:
        confs = [r.confidence for r in self.roles]
        confs += [e.confidence for e in self.relations]
        confs += [j.confidence for j in self.jural]
        return min(confs) if confs else 0.0


# ── the model port: a deterministic stub for tests ────────────────────────────

class StubModel:
    """A deterministic :data:`ports.ModelFn` (``str -> str``): it ignores the
    prompt and returns a *fixed* canned relation graph as JSON. Faithful to the
    real seam — a host's model likewise returns a completion string that
    :func:`construct_relational` decodes — but with no model runtime, so the
    gates are exercised deterministically. Construct with the proposal you want::

        model = StubModel({"roles": [...], "relations": [...], "jural": [...]})
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
        "Extract the relation graph of the following policy text: the roles "
        "(typed parties) it names, the relation edges between them (acts-for, "
        "provides-to, employs, owns, member-of, …), and any Hohfeldian jural "
        "position a role bears toward a counterparty (claim/privilege/power/"
        "immunity). For every element return the verbatim source SPAN, solver "
        "names and a confidence; give the relation composition table and any "
        "stated relation chains. Reply as JSON.\n\n" + text
    )


# ── the result ────────────────────────────────────────────────────────────────

@dataclass
class RelationalResult:
    """The outcome of a construction attempt. It carries a grounded,
    composable, correlativity-consistent relation graph XOR a rejection/
    escalation — never an ungrounded role and never a fabricated composite."""

    status: str                                  # extracted | rejected | escalated
    roles: tuple[Role, ...]
    edges: tuple[Edge, ...]                      # dimensioned RELATIONAL edges
    correlatives: tuple[CorrelativePosition, ...]
    flagged: tuple[str, ...]                     # rights missing a correlative
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


def _reject(reason: str, report: dict, prov: dict) -> RelationalResult:
    return RelationalResult("rejected", (), (), (), (), False, reason, report, prov)


def _escalate(reason: str, report: dict, prov: dict,
              *, flagged: tuple[str, ...] = (),
              correlatives: tuple[CorrelativePosition, ...] = ()) -> RelationalResult:
    return RelationalResult("escalated", (), (), correlatives, flagged, True,
                            reason, report, prov)


# ── provenance receipts ───────────────────────────────────────────────────────

def _receipt(text: str, *, role: str, span: str, name: str,
             confidence: float) -> dict[str, Any]:
    start = text.find(span) if span else -1
    end = start + len(span) if start >= 0 else -1
    return {"role": role, "name": name, "span": span, "start": start,
            "end": end, "confidence": confidence, "grounded": start >= 0}


def _all_receipts(text: str, p: RelationalProposal) -> list[dict[str, Any]]:
    out = [_receipt(text, role="role", span=r.span, name=r.name,
                    confidence=r.confidence) for r in p.roles]
    out += [_receipt(text, role=f"relation:{e.predicate or '?'}", span=e.span,
                     name=f"{e.subject} {e.predicate} {e.object}",
                     confidence=e.confidence) for e in p.relations]
    out += [_receipt(text, role=f"jural:{j.incident or '?'}", span=j.span,
                     name=f"{j.holder} {j.incident} {j.counterparty}".strip(),
                     confidence=j.confidence) for j in p.jural]
    return out


# ── correlativity-consistency (honesty floor #2, consumes deontic.correlative) ─

def _derive_correlatives(
    p: RelationalProposal,
) -> tuple[tuple[CorrelativePosition, ...], tuple[str, ...]]:
    """For every stated jural *advantage*, derive the counterparty position via
    :func:`deontic.incidents.correlative`. An advantage with no named
    counterparty has no one to bear the correlative — a right that does not tie
    out — and is FLAGGED. Returns ``(derived_correlatives, flagged)``.

    The correlative table itself is never reimplemented here: the mapping
    claim↔duty, privilege↔no-right, power↔liability, immunity↔disability comes
    straight from :func:`deontic.incidents.correlative`."""
    derived: list[CorrelativePosition] = []
    flagged: list[str] = []
    for j in p.jural:
        if not is_advantage(j.incident):
            # a stated burden (duty/no-right/liability/disability) needs no
            # counterparty to tie out — it is itself a correlative.
            continue
        if not j.counterparty:
            flagged.append(f"{j.holder or '?'}:{j.incident}")
            continue
        corr = correlative(j.incident)     # e.g. claim -> duty
        derived.append(CorrelativePosition(
            role=j.counterparty, incident=corr,
            toward=j.holder, source_incident=j.incident))
    return tuple(derived), tuple(flagged)


# ── composability (honesty floor #3, consumes RelationAlgebra.compose_path) ────

def _relation_vocabulary(p: RelationalProposal) -> set[Hashable]:
    """Every relation token that must live in the algebra's vocabulary so the
    fail-closed :class:`relation.RelationAlgebra` accepts the table."""
    vocab: set[Hashable] = set()
    for e in p.relations:
        if e.predicate:
            vocab.add(e.predicate)
    for c in p.composition:
        for key in ("a", "b", "result"):
            v = c.get(key, "")
            if v and v.upper() != "ESCALATE":
                vocab.add(v)
    for chain in p.chains:
        vocab.update(t for t in chain if t)
    for k, v in p.inverses.items():
        if k:
            vocab.add(k)
        if v:
            vocab.add(v)
    return vocab


def _build_algebra(p: RelationalProposal) -> RelationAlgebra:
    """Construct the :class:`relation.RelationAlgebra` from the proposal's
    vocabulary + composition table + inverses. ``"ESCALATE"`` rows map to the
    :data:`relation.ESCALATE` sentinel; every edge defaults to
    :data:`dimensions.Dimension.RELATIONAL`."""
    vocab = _relation_vocabulary(p)
    table: dict[tuple[Hashable, Hashable], Any] = {}
    for c in p.composition:
        a, b, result = c.get("a", ""), c.get("b", ""), c.get("result", "")
        if not (a and b):
            continue
        table[(a, b)] = ESCALATE if result.upper() == "ESCALATE" else (result or None)
    return RelationAlgebra(
        vocabulary=vocab,
        table=table,
        inverses={k: v for k, v in p.inverses.items() if k and v},
        default_dimension=Dimension.RELATIONAL,
    )


def _check_chains(algebra: RelationAlgebra,
                  p: RelationalProposal) -> tuple[bool, list[dict[str, Any]]]:
    """Fold every stated chain through :meth:`compose_path`. Returns
    ``(any_escalated, per_chain_report)``. A chain whose fold latches the
    :data:`relation.ESCALATE` sentinel is *contested* — the harness surfaces it
    rather than inventing a composite."""
    any_escalated = False
    report: list[dict[str, Any]] = []
    for chain in p.chains:
        result, escalated = algebra.compose_path(chain)
        any_escalated = any_escalated or escalated
        report.append({
            "chain": list(chain),
            "result": (repr(result) if result is ESCALATE
                       else (result if result is not None else None)),
            "escalated": escalated,
        })
    return any_escalated, report


# ── the reasoning-audit bridge (consumes interpret.interpret + interpret.audit)─

def _proposal_to_interp(p: RelationalProposal) -> dict:
    """Cast the relation graph as facts + rules so the existing auditor can check
    it: each role name is a fact, each relation edge is a rule
    ``subject => object`` (the relation entails its object party). A relation set
    that forces a party and its negation into the closure comes back
    inconsistent — the solver catching a broken graph — without this module
    reimplementing the audit."""
    facts = {r.name for r in p.roles if r.name}
    facts |= {e.subject for e in p.relations if e.subject}
    rules = [
        Rule(id=f"rel{i}", conditions=(e.subject,), consequence=e.object)
        for i, e in enumerate(p.relations)
        if e.subject and e.object
    ]
    return {"facts": facts, "rules": rules, "candidate": None}


def _audit_reasoning(text: str, p: RelationalProposal) -> dict:
    """Fill through :func:`interpret.interpret` (its ``parse`` seam driven by the
    decoded proposal) then verify with :func:`interpret.audit`."""
    interp = _interpret(text, parse=lambda _t: _proposal_to_interp(p))
    return _audit_interp(interp)


# ── the norm-contract confidence bridge (consumes the existing gate) ──────────

def _confidence_finding(min_conf: float, risk_class: str):
    pair = {"id": "relational", "solution": {"confidence": min_conf}}
    return norm_contract.check_confidence(pair, risk_class=risk_class)


def _has_escalate(findings) -> bool:
    return any(f.level is Level.ESCALATE for f in findings)


# ── the op ────────────────────────────────────────────────────────────────────

def construct_relational(
    text: str,
    *,
    model: ModelFn,
    risk_class: str = "C",
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> RelationalResult:
    """Construct a grounded relation graph from ``text``, or reject/escalate.

    The ``model`` (an injected :data:`ports.ModelFn`) proposes roles, relation
    edges, jural positions, a relation composition table and stated relation
    chains, each span-tagged with a confidence; deterministic gates over
    ``(proposal, text)`` then decide. In order of precedence:

      * **grounding** — any role/relation/jural span not a substring of ``text``
        is invented → REJECT (no subgraph);
      * **well-formedness** — a proposal with no roles, a relation edge whose
        endpoints are not declared roles, a jural position whose incident is
        outside :data:`deontic.incidents.INCIDENTS`, or a counterparty that is
        not a declared role → REJECT;
      * **correlativity-consistency** — a stated jural *advantage* with no
        counterparty to bear its :func:`deontic.incidents.correlative` position
        is a right that does not tie out → FLAG and ESCALATE, carrying the open
        rights in :attr:`RelationalResult.flagged`;
      * **composability** — a stated relation chain that folds to the
        :data:`relation.ESCALATE` sentinel via
        :meth:`relation.RelationAlgebra.compose_path` is contested → ESCALATE;
      * **audit** — :func:`interpret.audit` must find the relation set sound; an
        inconsistent graph → ESCALATE regardless of confidence;
      * **confidence floor** — :func:`norm_contract.check_confidence` /
        :data:`CONFIDENCE_FLOOR`; sub-floor → ESCALATE, regardless of any single
        high score.

    Only a proposal that is grounded AND correlativity-consistent AND composable
    AND audited AND at/above the floor is EXTRACTED, and only then is a subgraph
    returned — a tuple of :class:`reasoning.Edge` every one tagged
    :data:`dimensions.Dimension.RELATIONAL`, plus the derived counterparty
    correlatives.
    """
    prov: dict[str, Any] = {"text_len": len(text), "receipts": []}
    report: dict[str, Any] = {}

    # 0. Fill: consume the ModelFn seam and decode the proposal.
    raw = model(_build_prompt(text))
    try:
        proposal = RelationalProposal.from_json(raw) if isinstance(raw, str) \
            else RelationalProposal.from_dict(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        report["decode"] = {"ok": False, "error": str(exc)}
        return _reject("model returned an undecodable proposal", report, prov)

    prov["receipts"] = _all_receipts(text, proposal)

    # 1. Grounding (honesty floor #1): reject any invented span.
    invented: list[str] = []
    invented += [r.span for r in proposal.roles if not r.grounded_in(text)]
    invented += [e.span for e in proposal.relations if not e.grounded_in(text)]
    invented += [j.span for j in proposal.jural if not j.grounded_in(text)]
    report["grounding"] = {"ok": not invented, "invented": invented}
    if invented:
        return _reject(
            f"ungrounded element(s) — span not found in text: {invented!r}",
            report, prov)

    # 2. Well-formedness: at least one role; relation endpoints and jural
    #    holder/counterparty resolve to declared roles; incidents are valid.
    role_names = {r.name for r in proposal.roles if r.name}
    problems: list[str] = []
    if not proposal.roles:
        problems.append("no roles proposed")
    for e in proposal.relations:
        if not (e.subject and e.predicate and e.object):
            problems.append(f"malformed relation edge {e.span!r}")
        elif e.subject not in role_names or e.object not in role_names:
            problems.append(
                f"relation edge references an undeclared role: "
                f"{e.subject} {e.predicate} {e.object}")
    for j in proposal.jural:
        if j.incident not in _INCIDENTS:
            problems.append(f"unknown incident {j.incident!r}")
        elif j.holder not in role_names:
            problems.append(f"jural holder is an undeclared role: {j.holder!r}")
        elif j.counterparty and j.counterparty not in role_names:
            problems.append(
                f"jural counterparty is an undeclared role: {j.counterparty!r}")
    wf_ok = not problems
    report["wellformed"] = {"ok": wf_ok, "problems": problems}
    if not wf_ok:
        return _reject("malformed proposal: " + "; ".join(problems), report, prov)

    # 3. Correlativity-consistency (honesty floor #2, consumes deontic.correlative):
    #    a stated advantage with no counterparty → FLAG + escalate.
    correlatives, flagged = _derive_correlatives(proposal)
    report["correlativity"] = {
        "ok": not flagged,
        "flagged": list(flagged),
        "derived": [c.as_dict() for c in correlatives],
    }
    if flagged:
        return _escalate(
            "correlativity flag — right(s) asserted with no correlative "
            "counterparty: " + repr(list(flagged)),
            report, prov, flagged=flagged, correlatives=correlatives)

    # 4. Composability (honesty floor #3, consumes RelationAlgebra.compose_path):
    #    a contested chain (folds to ESCALATE) → escalate.
    try:
        algebra = _build_algebra(proposal)
    except ValueError as exc:
        report["composability"] = {"ok": False, "algebra_error": str(exc)}
        return _reject("relation algebra vocabulary/table mismatch: " + str(exc),
                       report, prov)
    chains_escalated, chain_report = _check_chains(algebra, proposal)
    report["composability"] = {"ok": not chains_escalated, "chains": chain_report}
    if chains_escalated:
        return _escalate(
            "composability escalate — a stated relation chain is contested "
            "(compose_path returned the ESCALATE sentinel)",
            report, prov, correlatives=correlatives)

    # 5. Audit: consume interpret.interpret + interpret.audit.
    audit_report = _audit_reasoning(text, proposal)
    audited = audit_report["verdict"] == "sound"
    report["audit"] = {"verdict": audit_report["verdict"],
                       "reasons": audit_report["reasons"]}
    if not audited:
        # Confidence is never trusted alone: an unsound graph escalates no
        # matter how high the self-reported score.
        return _escalate("audit unsound — " + "; ".join(audit_report["reasons"]),
                         report, prov, correlatives=correlatives)

    # 6. Confidence floor: NT-9 plus a hard floor independent of risk_class.
    min_conf = proposal.min_confidence()
    nt9 = _confidence_finding(min_conf, risk_class)
    sub_floor = min_conf < confidence_floor or _has_escalate(nt9)
    report["confidence"] = {"min": min_conf, "floor": confidence_floor,
                            "ok": not sub_floor,
                            "nt9": [f.to_dict() for f in nt9]}
    if sub_floor:
        return _escalate(
            f"sub-floor confidence {min_conf} < {confidence_floor}",
            report, prov, correlatives=correlatives)

    # 7. Extract — grounded, correlativity-consistent, composable, audited,
    #    at/above the floor.
    edges = tuple(e.to_edge() for e in proposal.relations)
    assert all(r["grounded"] for r in prov["receipts"]), \
        "invariant: extracted subgraph has an ungrounded receipt"
    assert all(e.dimension is Dimension.RELATIONAL for e in edges), \
        "invariant: a returned relational edge is not tagged RELATIONAL"
    report["extracted"] = True
    return RelationalResult(
        "extracted", proposal.roles, edges, correlatives, (),
        False, "grounded, correlativity-consistent, composable, audited "
        "and at/above the floor",
        report, prov)
