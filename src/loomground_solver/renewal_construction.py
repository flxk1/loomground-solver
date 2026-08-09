# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Renewal construction (the contract-lifecycle slice of the TEMPORAL fact-
dimension) — generic contract text → a *grounded* lifecycle structure (a contract
**term**, its **renewal** mechanic, and any **reversion** of rights), or an honest
REJECT / ESCALATE. An [I]-tier op: the **model fills** the lifecycle, the
**contract gates** it, the harness **escalates** the open.

Sibling to :mod:`temporal_construction`. Where that op extracts *when a procedure
runs* — its states, transitions, orderings and deadlines — this op extracts *how
long a contract lives and what happens at its edge*: the term (a duration or an
end date), the renewal that carries it forward (``auto`` — renews unless notice is
given — or ``option`` — renews only on exercise — with a renewal **period** and,
for an auto-renewal, a **notice** window), and the reversion of rights at a named
event ("all rights revert to the Author on termination"). It hands the renewal
back on the *existing* typed primitives and the reversions as a subgraph of
:class:`reasoning.Edge` tagged :data:`dimensions.Dimension.TEMPORAL`.

It CONSUMES what exists rather than regrowing it:

  * the fill is the injected :data:`ports.ModelFn` (``str -> str``): the package
    never binds a model; the completion is a JSON proposal it decodes;
  * the **term** is a **consumed** :class:`temporal.Term`, the **renewal** a
    **consumed** :class:`temporal.RenewalRule` whose ``period``/``notice`` are
    **consumed** :class:`temporal.Duration` values. This module never
    reimplements ``Term``/``RenewalRule``, never re-parses a renewal period, never
    re-derives a notice deadline — it only *extracts* the kind, the spans and the
    offsets and hands them to the type layer that already validates them (the
    CONSUME-DON'T-REGROW discipline);
  * the reasoning is verified through :func:`interpret.interpret` (the fill seam,
    driven here by the decoded lifecycle) and :func:`interpret.audit` (the solver
    checking the lifecycle chain closes coherently) — the audit is *not*
    reimplemented;
  * the confidence floor is the existing contract:
    :func:`norm_contract.check_confidence` / :data:`norm_contract.CONFIDENCE_FLOOR`;
  * a reversion is the existing dimensioned :class:`reasoning.Edge`, tagged
    :data:`dimensions.Dimension.TEMPORAL`.

The renewal-honesty floor is committed, not optional:

  1. **grounding** — every term / renewal / notice / reversion span must be a
     *substring of the input text*. A span that is not found is REJECTED as
     invented. The harness never asserts an ungrounded term or renewal.
  2. **kind well-formedness + kind-ambiguity** — the renewal ``kind`` must be
     ``auto`` or ``option`` **and grounded** by a distinguishing span. If the text
     does not distinguish the mechanic (the model returns an ambiguous kind, or
     the kind's evidencing span is absent), the op ESCALATES — it NEVER guesses
     whether a renewal is automatic or optional.
  3. **auto-notice** — an ``auto`` renewal without a *grounded* notice period is
     FLAGGED (surfaced on ``flagged``) and the construction ESCALATES: an
     auto-renewal with no notice window is a live trap, not something to accept
     silently.
  4. **reversion-anchoring** — a reversion must anchor to a *grounded* event. A
     reversion whose anchoring event is absent or ungrounded is FLAGGED and the
     construction ESCALATES — you cannot resolve a reversion that hangs on nothing.
  5. **confidence is never trusted alone** — a high self-reported score cannot buy
     an acceptance past an ambiguous kind, a missing notice or an unanchored
     reversion; sub-floor confidence ESCALATES regardless.

Pure stdlib (``json``, ``dataclasses``, ``typing``). No governance, no corpus, no
domain: :func:`construct_renewal` takes a generic contract-text ``str`` — never a
corpus-coupled object. The solver is corpus-free; this op imports neither
``loomground_legal`` nor ``loomground_versum``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from . import norm_contract
from .dimensions import Dimension
from .interpret import audit as _audit_interp
from .interpret import interpret as _interpret
from .norm_contract import CONFIDENCE_FLOOR, Level
from .ports import ModelFn
from .reasoning import Edge
from .subsumption import Rule
from .temporal import Date, Duration, RenewalRule, TemporalError, Term

_RENEWAL_KINDS = ("auto", "option")


# ── the proposal schema the ModelFn returns ───────────────────────────────────

@dataclass(frozen=True)
class TermClaim:
    """The contract term the text declares: a ``duration`` (ISO 8601) **or** an
    ``end`` date, an optional ``start``, with its verbatim source span. The
    duration/end are validated by :class:`temporal.Duration`/:class:`temporal.Date`
    at build time, not by this module."""

    span: str = ""
    start: str = ""
    end: str = ""
    duration: str = ""
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "TermClaim":
        return cls(span=str(d.get("span", "")), start=str(d.get("start", "")),
                   end=str(d.get("end", "")), duration=str(d.get("duration", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def well_formed(self) -> bool:
        # A term declares end XOR duration (both is a drafting conflict the type
        # refuses to paper over); at least one lifecycle field must be present.
        if self.end and self.duration:
            return False
        if not (self.start or self.end or self.duration):
            return False
        # the offered temporal values must parse (malformed, not guessed)
        if self.duration and self._parsed_duration() is None:
            return False
        if self.end and not _parses_date(self.end):
            return False
        if self.start and not _parses_date(self.start):
            return False
        return True

    def _parsed_duration(self) -> "Duration | None":
        try:
            return Duration.parse(self.duration)
        except TemporalError:
            return None

    def to_term(self, renewal: Optional[RenewalRule]) -> Term:
        """CONSUME :class:`temporal.Term` — never a home-grown term type."""
        return Term(
            start=Date(self.start) if self.start else None,
            end=Date(self.end) if self.end else None,
            duration=Duration.parse(self.duration) if self.duration else None,
            renewal=renewal,
        )


@dataclass(frozen=True)
class RenewalClaim:
    """The renewal mechanic: a ``kind`` (``auto`` or ``option``), a renewal
    ``period`` (ISO 8601), an optional ``notice`` period (ISO 8601, meaningful for
    ``auto``), the verbatim clause ``span``, and the ``kind_span`` — the specific
    phrase that *distinguishes* auto from option. ``notice_span`` grounds the
    notice period. The period/notice are validated by :class:`temporal.Duration`."""

    kind: str = ""
    period: str = ""
    notice: str = ""
    span: str = ""
    kind_span: str = ""
    notice_span: str = ""
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "RenewalClaim":
        return cls(kind=str(d.get("kind", "")).strip().lower(),
                   period=str(d.get("period", d.get("duration", ""))),
                   notice=str(d.get("notice", "")),
                   span=str(d.get("span", "")),
                   kind_span=str(d.get("kind_span", "")),
                   notice_span=str(d.get("notice_span", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def parsed_period(self) -> "Duration | None":
        try:
            return Duration.parse(self.period)
        except TemporalError:
            return None

    def parsed_notice(self) -> "Duration | None":
        if not self.notice:
            return None
        try:
            return Duration.parse(self.notice)
        except TemporalError:
            return None

    @property
    def has_notice(self) -> bool:
        return bool(self.notice)

    def well_formed(self) -> bool:
        # A kind and a parseable period are structural minima; a *present* notice
        # must parse. Whether the kind is auto/option/ambiguous is a later gate.
        if not self.kind or self.parsed_period() is None:
            return False
        if self.notice and self.parsed_notice() is None:
            return False
        return True

    def kind_grounded(self, text: str) -> bool:
        """The renewal mechanic is grounded only when a distinguishing span is
        present in the text — the evidence that it is auto vs option."""
        return bool(self.kind_span) and self.kind_span in text

    def to_rule(self) -> RenewalRule:
        """CONSUME :class:`temporal.RenewalRule` over :class:`temporal.Duration` —
        never a re-grown renewal type or re-derived renewal arithmetic."""
        return RenewalRule(
            kind=self.kind,
            period=Duration.parse(self.period),
            notice=Duration.parse(self.notice) if self.notice else None,
        )


@dataclass(frozen=True)
class ReversionClaim:
    """A reversion of rights: ``right`` reverts at a named ``event``. ``event_span``
    grounds the anchoring event; ``span`` is the verbatim reversion clause."""

    right: str = ""
    event: str = ""
    span: str = ""
    event_span: str = ""
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "ReversionClaim":
        return cls(right=str(d.get("right", d.get("subject", ""))),
                   event=str(d.get("event", d.get("anchor", ""))),
                   span=str(d.get("span", "")),
                   event_span=str(d.get("event_span", "")),
                   confidence=float(d.get("confidence", 1.0)))

    def well_formed(self) -> bool:
        # A missing/ungrounded event is *unanchored* (a later FLAG), not malformed;
        # only a right-less, span-less reversion is structurally broken.
        return bool(self.right) and bool(self.span)

    def anchored(self, text: str) -> bool:
        """A reversion is anchored only when its event is named AND that event is
        grounded by a span present in the text."""
        return bool(self.event) and bool(self.event_span) and self.event_span in text

    def to_edge(self, source_pair: str) -> Edge:
        return Edge(
            subject=self.right,
            predicate="reverts-at",
            object=self.event,
            dimension=Dimension.TEMPORAL,
            weight=max(0.0, min(1.0, self.confidence)),
            source_pair=source_pair,
        )


@dataclass(frozen=True)
class NoticeFlag:
    """An ``auto`` renewal with no grounded notice period. Surfaced, never
    silently accepted — an auto-renewal without a notice window is a live trap."""

    kind: str
    period: str
    reason: str = "auto-renewal without a grounded notice period"

    def as_dict(self) -> dict[str, Any]:
        return {"flag": "auto-without-notice", "kind": self.kind,
                "period": self.period, "reason": self.reason}


@dataclass(frozen=True)
class ReversionFlag:
    """A reversion whose anchoring event is absent or ungrounded. Surfaced, never
    resolved — you cannot hang a reversion on nothing."""

    right: str
    event: str
    reason: str = "reversion anchor is not a grounded event in the text"

    def as_dict(self) -> dict[str, Any]:
        return {"flag": "unanchored-reversion", "right": self.right,
                "event": self.event, "reason": self.reason}


@dataclass(frozen=True)
class RenewalProposal:
    """A model's proposed contract-lifecycle structure. Convention, not truth —
    every claim is subject to the gates before any of it becomes a
    :class:`temporal.Term`, a :class:`temporal.RenewalRule` or a grounded Edge."""

    term: Optional[TermClaim] = None
    renewal: Optional[RenewalClaim] = None
    reversions: tuple[ReversionClaim, ...] = ()

    @classmethod
    def from_dict(cls, d: dict) -> "RenewalProposal":
        term = d.get("term")
        renewal = d.get("renewal")
        return cls(
            term=TermClaim.from_dict(term) if term else None,
            renewal=RenewalClaim.from_dict(renewal) if renewal else None,
            reversions=tuple(
                ReversionClaim.from_dict(r) for r in (d.get("reversions") or ())),
        )

    @classmethod
    def from_json(cls, raw: str) -> "RenewalProposal":
        return cls.from_dict(json.loads(raw))

    def all_claims(self) -> tuple:
        out: list = []
        if self.term is not None:
            out.append(self.term)
        if self.renewal is not None:
            out.append(self.renewal)
        out.extend(self.reversions)
        return tuple(out)


# ── the model port: a deterministic stub for tests ────────────────────────────

class StubModel:
    """A deterministic :data:`ports.ModelFn` (``str -> str``): it ignores the
    prompt and returns a *fixed* canned lifecycle as JSON. Faithful to the real
    seam — a host's model likewise returns a completion string that
    :func:`construct_renewal` decodes — but with no model runtime, so the gates
    are exercised deterministically. Construct with the proposal to propose::

        model = StubModel({"term": {...}, "renewal": {...}, "reversions": [...]})
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
        "Extract the lifecycle of the following contract text. Give the TERM "
        "(a start, and an end date OR an ISO 8601 duration), the RENEWAL mechanic "
        "(kind: auto or option; the renewal period as an ISO 8601 duration; for an "
        "auto renewal the notice period as an ISO 8601 duration; and the span that "
        "DISTINGUISHES auto from option), and any REVERSION of rights (what reverts, "
        "the anchoring event, its span). Supply the verbatim source SPAN and a "
        "confidence for each. If the text does not distinguish auto from option, "
        "say so — do not guess. Reply as JSON.\n\n" + text
    )


# ── the result ────────────────────────────────────────────────────────────────

@dataclass
class RenewalResult:
    """The outcome of a renewal-construction attempt. It carries the grounded
    lifecycle — a :class:`temporal.Term`, a :class:`temporal.RenewalRule`, and
    TEMPORAL-tagged reversion edges — XOR a rejection / escalation. It never
    presents an ungrounded term, a *guessed* renewal kind, an auto-renewal with no
    notice window, or a reversion hung on nothing."""

    status: str                                  # extracted | rejected | escalated
    term: Optional[Term]
    renewal: Optional[RenewalRule]
    reversions: tuple[Edge, ...]
    flagged: tuple[Any, ...]
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


def _reject(reason, report, prov, flagged=()) -> RenewalResult:
    return RenewalResult("rejected", None, None, (), tuple(flagged), False,
                         reason, report, prov)


def _escalate(reason, report, prov, flagged=()) -> RenewalResult:
    return RenewalResult("escalated", None, None, (), tuple(flagged), True,
                         reason, report, prov)


# ── grounding helpers (honesty floor #1) ──────────────────────────────────────

def _parses_date(value: str) -> bool:
    try:
        Date(value)
        return True
    except TemporalError:
        return False


def _span_of(claim) -> str:
    return getattr(claim, "span", "")


def _receipt(claim, text: str) -> dict[str, Any]:
    span = _span_of(claim)
    start = text.find(span) if span else -1
    return {"kind": type(claim).__name__, "span": span, "start": start,
            "end": start + len(span) if start >= 0 else -1,
            "grounded": start >= 0}


def _grounding_spans(proposal: RenewalProposal) -> list[tuple[str, str]]:
    """The spans the grounding gate rejects-if-invented: the term clause, the
    renewal clause, the notice clause (when a notice is present) and every
    reversion clause. The KIND-distinguishing span is checked by the kind gate
    (an ungrounded kind ESCALATES as ambiguous, it does not REJECT), and a
    reversion's EVENT span is checked by the anchoring gate (an ungrounded event
    FLAGS, it does not REJECT)."""
    spans: list[tuple[str, str]] = []
    if proposal.term is not None:
        spans.append(("term", proposal.term.span))
    if proposal.renewal is not None:
        spans.append(("renewal", proposal.renewal.span))
        if proposal.renewal.has_notice:
            spans.append(("notice", proposal.renewal.notice_span))
    for r in proposal.reversions:
        spans.append(("reversion", r.span))
    return spans


# ── the reasoning-audit bridge (consumes interpret.interpret + interpret.audit)─

def _lifecycle_interp(proposal: RenewalProposal,
                      anchored: tuple[ReversionClaim, ...]) -> dict:
    """Cast the grounded lifecycle as facts + rules so the existing auditor can
    check the chain closes coherently: the contract is effective, the term ends,
    the renewal carries the term forward, and each reversion fires at term end.
    Reuses the solver's forward-chaining audit rather than reimplementing one."""
    facts: set[str] = {"contract_effective"}
    rules: list[Rule] = []
    if proposal.term is not None:
        rules.append(Rule(id="lifecycle:term", conditions=("contract_effective",),
                          consequence="term_end"))
    if proposal.renewal is not None:
        rules.append(Rule(id="lifecycle:renew", conditions=("term_end",),
                          consequence="renewal_term"))
    for i, r in enumerate(anchored):
        rules.append(Rule(id=f"lifecycle:revert:{i}", conditions=("term_end",),
                          consequence=f"reversion:{r.event}"))
    return {"facts": facts, "rules": rules, "candidate": None}


def _audit_reasoning(text: str, proposal: RenewalProposal,
                     anchored: tuple[ReversionClaim, ...]) -> dict:
    """Fill through :func:`interpret.interpret` (its ``parse`` seam driven by the
    decoded lifecycle) then verify with :func:`interpret.audit`."""
    interp = _interpret(text, parse=lambda _t: _lifecycle_interp(proposal, anchored))
    return _audit_interp(interp)


# ── the norm-contract bridge (consumes the existing confidence gate) ──────────

def _confidence_finding(min_conf: float, risk_class: str):
    """NT-9 via :func:`norm_contract.check_confidence`."""
    pair = {"id": "renewal", "solution": {"confidence": min_conf}}
    return norm_contract.check_confidence(pair, risk_class=risk_class)


def _has_escalate(findings) -> bool:
    return any(f.level is Level.ESCALATE for f in findings)


# ── the op ────────────────────────────────────────────────────────────────────

def construct_renewal(
    text: str,
    *,
    model: ModelFn,
    risk_class: str = "C",
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> RenewalResult:
    """Construct a grounded contract-lifecycle structure from ``text``, or reject /
    escalate.

    The ``model`` (an injected :data:`ports.ModelFn`) proposes a term + renewal +
    reversions; deterministic gates over ``(proposal, text)`` then decide. The
    gates, in order of precedence:

      * **well-formedness** — a term declaring both end and duration (or none), a
        renewal with no kind / an unparseable period / an unparseable present
        notice, or a right-less reversion is malformed → REJECT;
      * **grounding** (floor #1) — any term / renewal / notice / reversion span
        that is not a substring of ``text`` is invented → REJECT (no term, no
        renewal is returned);
      * **kind-ambiguity** (floor #2) — the renewal ``kind`` must be ``auto`` or
        ``option`` AND grounded by a distinguishing span. An ambiguous or
        ungrounded kind → ESCALATE. The mechanic is NEVER guessed;
      * **auto-notice** (floor #3) — an ``auto`` renewal with no grounded notice is
        FLAGGED and the construction ESCALATES with the open notice surfaced;
      * **reversion-anchoring** (floor #4) — a reversion whose event is absent or
        ungrounded is FLAGGED and the construction ESCALATES with the open anchor;
      * **audit** — :func:`interpret.audit` must find the lifecycle chain sound;
      * **confidence floor** — NT-9 / :data:`CONFIDENCE_FLOOR` over every claim;
        sub-floor → ESCALATE, regardless of any high self-reported score.

    Only a proposal that is well-formed, grounded, has an unambiguous grounded
    kind, carries a notice when it renews automatically, anchors every reversion on
    a grounded event, audits sound and sits at/above the floor is EXTRACTED — with
    the term on :class:`temporal.Term`, the renewal on :class:`temporal.RenewalRule`
    over :class:`temporal.Duration`, and reversions as
    :data:`Dimension.TEMPORAL`-tagged :class:`reasoning.Edge`. Escalation is a pass.
    """
    prov: dict[str, Any] = {"receipts": []}
    report: dict[str, Any] = {}

    # 0. Fill: consume the ModelFn seam and decode the proposal.
    raw = model(_build_prompt(text))
    try:
        proposal = RenewalProposal.from_json(raw) if isinstance(raw, str) \
            else RenewalProposal.from_dict(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        report["decode"] = {"ok": False, "error": str(exc)}
        return _reject("model returned an undecodable proposal", report, prov)

    prov["receipts"] = [_receipt(c, text) for c in proposal.all_claims()]

    # A renewal op with no renewal to construct is nothing to do — honest reject.
    if proposal.renewal is None:
        report["present"] = {"ok": False, "renewal": False}
        return _reject("no renewal mechanic proposed — nothing to construct",
                       report, prov)

    # 1. Well-formedness of every proposed claim.
    malformed = [type(c).__name__ for c in proposal.all_claims() if not c.well_formed()]
    report["wellformed"] = {"ok": not malformed, "malformed": malformed}
    if malformed:
        return _reject(
            f"malformed lifecycle claim(s) — end/duration conflict, missing kind, "
            f"or unparseable period/notice: {malformed!r}", report, prov)

    # 2. Grounding (honesty floor #1): reject any invented span.
    invented = [span for _label, span in _grounding_spans(proposal)
                if not (span and span in text)]
    report["grounding"] = {"ok": not invented, "invented": invented}
    if invented:
        return _reject(
            f"ungrounded lifecycle claim(s) — span not found in text: {invented!r}",
            report, prov)

    # 3. Kind-ambiguity (honesty floor #2): the mechanic must be auto/option AND
    #    grounded. If the text does not distinguish it → escalate, never guess.
    renewal = proposal.renewal
    kind_ok = renewal.kind in _RENEWAL_KINDS and renewal.kind_grounded(text)
    report["kind"] = {"ok": kind_ok, "kind": renewal.kind,
                      "kind_grounded": renewal.kind_grounded(text),
                      "allowed": list(_RENEWAL_KINDS)}
    if not kind_ok:
        if renewal.kind not in _RENEWAL_KINDS:
            why = (f"ambiguous renewal mechanic ({renewal.kind!r}) — the text does "
                   "not distinguish auto from option")
        else:
            why = (f"renewal mechanic ({renewal.kind}) not grounded — no "
                   "distinguishing span in the text; cannot confirm the mechanic")
        return _escalate(why + "; the renewal kind is never guessed", report, prov)

    # 4. Auto-notice (honesty floor #3): an auto renewal without a grounded notice
    #    is a live trap → flag it and escalate with the open notice surfaced.
    notice_flag: tuple = ()
    auto_needs_notice = renewal.kind == "auto" and not renewal.has_notice
    if auto_needs_notice:
        notice_flag = (NoticeFlag(kind=renewal.kind, period=renewal.period),)
    report["auto_notice"] = {"ok": not auto_needs_notice, "kind": renewal.kind,
                             "has_notice": renewal.has_notice,
                             "flagged": [f.as_dict() for f in notice_flag]}
    if auto_needs_notice:
        return _escalate(
            "auto-renewal without a grounded notice period — cannot resolve the "
            "notice deadline; a human must supply the notice window",
            report, prov, flagged=notice_flag)

    # 5. Reversion-anchoring (honesty floor #4): every reversion must anchor to a
    #    grounded event. An unanchored reversion is flagged and the op escalates.
    unanchored = tuple(
        ReversionFlag(right=r.right, event=r.event)
        for r in proposal.reversions if not r.anchored(text)
    )
    report["reversion_anchoring"] = {
        "ok": not unanchored,
        "reversions": len(proposal.reversions),
        "flagged": [f.as_dict() for f in unanchored],
    }
    if unanchored:
        return _escalate(
            "unanchored reversion(s) — anchor names no grounded event: "
            + ", ".join(f"{f.right!r} @ {f.event!r}" for f in unanchored),
            report, prov, flagged=unanchored)

    anchored_reversions = proposal.reversions   # all anchored past this point

    # 6. Audit: consume interpret.interpret + interpret.audit over the lifecycle
    #    chain. Confidence is never trusted alone — an unsound chain escalates.
    audit_report = _audit_reasoning(text, proposal, anchored_reversions)
    audited = audit_report["verdict"] == "sound"
    report["audit"] = {"verdict": audit_report["verdict"],
                       "reasons": audit_report["reasons"]}
    if not audited:
        return _escalate(
            "audit unsound — " + "; ".join(audit_report["reasons"]), report, prov)

    # 7. Confidence floor: NT-9 plus a hard floor independent of risk_class, over
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

    # 8. Extract — well-formed, grounded, unambiguous grounded kind, notice present
    #    when auto, anchored reversions, audited sound, at/above the floor. BUILD
    #    the renewal on temporal.RenewalRule, the term on temporal.Term (both
    #    CONSUMED, never re-grown), and the reversions as TEMPORAL-tagged edges.
    try:
        renewal_rule = renewal.to_rule()
        term = proposal.term.to_term(renewal_rule) if proposal.term is not None \
            else Term(renewal=renewal_rule)
    except TemporalError as exc:
        # A drafting conflict the type layer refuses to paper over (e.g. term end
        # before start) — surfaced honestly, never coerced.
        report["build"] = {"ok": False, "error": str(exc)}
        return _reject(f"lifecycle does not build on the typed primitives: {exc}",
                       report, prov)

    reversions = tuple(r.to_edge(f"renewal:reversion:{i}")
                       for i, r in enumerate(anchored_reversions))

    # Belt-and-suspenders invariants: the renewal IS the consumed primitive, and
    # every reversion edge is TEMPORAL-tagged.
    assert isinstance(renewal_rule, RenewalRule) and renewal_rule.kind in _RENEWAL_KINDS
    assert isinstance(renewal_rule.period, Duration)
    assert renewal_rule.notice is None or isinstance(renewal_rule.notice, Duration)
    assert isinstance(term, Term) and term.renewal is renewal_rule
    assert all(e.dimension is Dimension.TEMPORAL for e in reversions), \
        "invariant: a grounded reversion edge is not TEMPORAL-tagged"

    report["extracted"] = {"kind": renewal_rule.kind,
                           "period": renewal_rule.period.iso,
                           "notice": renewal_rule.notice.iso if renewal_rule.notice else None,
                           "reversions": len(reversions)}
    return RenewalResult(
        "extracted", term, renewal_rule, reversions, (), False,
        "grounded, unambiguous grounded kind, notice present when auto, anchored "
        "reversions, audited sound and at/above the floor; term on temporal.Term, "
        "renewal on temporal.RenewalRule/Duration, reversions TEMPORAL-tagged",
        report, prov)
