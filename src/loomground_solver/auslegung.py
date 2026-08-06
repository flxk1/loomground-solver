# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Auslegung (O36–O45) — per-element interpretation via the canons of construction.

Selecting a canon set is *data* (see :mod:`loomground_solver.canons`); turning a
canon into a reading of a concrete element is *judgment*. This module is that
judgment step, run as an **[I]-tier** operation: the injected model FILLS a
reading per canon, the reasoning contract GATES each fill, and the genuinely
open call ESCALATES rather than being answered.

The shape of one interpretation:

    (a) SELECT   the ordered canon set + tie-breaker + wording cap for the
                 family — ``canons.canon_set_for(family)`` (already built).
    (b) O36      ambiguity: an element with a *settled* reading needs no canons —
                 return it and never call the model (short-circuit).
    (c) FILL     for EACH canon the model PROPOSES a reading, GROUNDED to a span
                 of the text, expressed in the interpret notation
                 (``fact: span`` / ``rule: span => reading`` / ``claim: reading``
                 / ``conf: 0..1``). Each fill is GATED:
                   * grounding + verify — :func:`interpret.interpret` parses it
                     and :func:`interpret.audit` checks the reading is entailed
                     by its span (an ungrounded / unentailed reading is the
                     solver catching a hallucinated leap, and is dropped);
                   * evidence — :func:`contract.check_evidence`;
                   * warrant — :func:`contract.check_warrants` (the interpretive
                     move must name the canon that licenses it);
                   * confidence floor — :func:`norm_contract.check_confidence`
                     (sub-floor confidence never answers; it escalates). A score
                     is necessary, never sufficient: a thin grounding or a failed
                     audit drops the reading regardless of how confident it is.
    (d) O43      detect divergence across the surviving canon-readings.
    (e) O45      converge  → synthesise the agreed reading.
    (f) O44      diverge   → weight by the ``CanonSet.tiebreaker`` (the canon the
                 family lets break a tie).
    (g) O37      WORTLAUTGRENZE — the grammatical (wording) reading is the OUTER
                 LIMIT (``CanonSet.cap``). A synthesised/weighted reading the
                 wording cannot bear is *contra legem* → ESCALATE; it is never
                 returned as the reading. Where the tradition recognises no such
                 cap (``cap == ""``) there is no outer limit to cross.
    (h) O48      the tie-breaker does not settle the divergence (the tie-breaking
                 canon produced no gated reading) → ESCALATE: genuinely open.

Dependency direction: this module is domain-free. It takes the element text, the
surrounding norm text and a family id — never a ``loomground_legal`` object.

CONSUMES: ``canons.canon_set_for`` / ``CanonSet``, ``ports.ModelFn`` (the
injected model — never a real LLM here), ``interpret.interpret`` /
``interpret.audit`` (fill + verify), and the contract gate functions
``contract.check_evidence`` / ``contract.check_warrants`` /
``norm_contract.check_confidence``. It reimplements none of them — it wraps them.

Pure stdlib. Gates deterministic; the fill (the model) is not.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .canons import CanonSet, canon_set_for
from .contract import check_evidence, check_warrants
from .interpret import audit as audit_reasoning
from .interpret import interpret as interpret_reasoning
from .norm_contract import Level, check_confidence
from .ports import ModelFn

__all__ = [
    "ReadingResult",
    "StubModel",
    "interpret_element",
    "canon_prompt",
]

# The sentinel a fill prompt carries so a canned StubModel (and only a stub —
# a real model reads the natural-language instruction) can tell which canon is
# being asked for. Deterministic, unambiguous, easy to match.
_CANON_SENTINEL = "[[auslegung-canon:{canon}]]"
_CANON_RE = re.compile(r"\[\[auslegung-canon:(.+?)\]\]")


# ── result ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReadingResult:
    """The outcome of interpreting one element.

    Either a *grounded* reading that cleared every gate and stayed within the
    wording cap, or an escalation — never a reading that crosses the cap and
    never an ungrounded one.

    ``reading``          the reading, or ``None`` when escalated.
    ``escalated``        True iff the call belongs to a human (open / contra legem
                         / sub-floor). Escalation is a valid, deliberate outcome.
    ``reason``           human-readable why (which O-step fired).
    ``canon_readings``   per-canon record: reading, span, confidence, gate status.
    ``tiebreaker_used``  True iff the reading was chosen by the tie-breaking canon
                         (a divergence the family's tie-breaker settled).
    ``gate_report``      per-canon gate outcome (audit verdict, confidence, status).
    ``provenance``       family, canon-set label, ordered canons, tie-breaker, cap.
    """

    reading: Optional[str]
    escalated: bool
    reason: str
    canon_readings: dict = field(default_factory=dict)
    tiebreaker_used: bool = False
    gate_report: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "reading": self.reading,
            "escalated": self.escalated,
            "reason": self.reason,
            "canon_readings": dict(self.canon_readings),
            "tiebreaker_used": self.tiebreaker_used,
            "gate_report": dict(self.gate_report),
            "provenance": dict(self.provenance),
        }


# ── the fill prompt + a deterministic stub model ─────────────────────────────

def canon_prompt(canon: str, element: str, text: str) -> str:
    """The fill prompt for one canon: asks the model to propose a reading under
    ``canon``, grounded to a span, in the interpret notation. Carries a sentinel
    so a canned :class:`StubModel` can route by canon."""
    return (
        _CANON_SENTINEL.format(canon=canon) + "\n"
        f"Read the element under the '{canon}' canon of construction.\n"
        f"Element: {element}\n"
        f"Surrounding text: {text}\n"
        "Answer in the interpret notation, grounding the reading to a span of "
        "the text you actually rely on:\n"
        "  fact: <span drawn verbatim from the text>\n"
        "  rule: <span> => <the reading it yields under this canon>\n"
        "  claim: <the reading>\n"
        "  conf: <0..1>\n"
    )


def _canon_of_prompt(prompt: str) -> str:
    m = _CANON_RE.search(prompt or "")
    return m.group(1) if m else ""


class StubModel:
    """A deterministic, canned :class:`ports.ModelFn` for tests — never an LLM.

    Built from ``{canon: fill_notation}``; on each call it reads the canon from
    the prompt sentinel and returns that canon's canned fill (or ``default`` for
    an un-mapped canon — ``""`` by default, which reads as *no reading*). Every
    prompt it sees is recorded in ``calls`` so a test can assert the model was —
    or, for the O36 short-circuit, was NOT — called.
    """

    def __init__(self, fills: dict[str, str], *, default: str = "") -> None:
        self.fills = dict(fills)
        self.default = default
        self.calls: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.fills.get(_canon_of_prompt(prompt), self.default)


# ── gate helpers ─────────────────────────────────────────────────────────────

def _has(findings, level: Level) -> bool:
    return any(f.level is level for f in findings)


def _parse_conf(raw: str) -> Optional[float]:
    """Pull the ``conf:`` line out of a fill (the interpret parser ignores it).
    Absent or unparseable ⇒ ``None`` — which the confidence gate treats as *no
    stated confidence*, a violation, not a silent pass."""
    for line in (raw or "").splitlines():
        prefix, sep, body = line.partition(":")
        if sep and prefix.strip().lower() == "conf":
            try:
                return float(body.strip())
            except ValueError:
                return None
    return None


def _gate_canon(canon: str, element: str, raw: str, *, risk_class: str) -> dict:
    """FILL one canon and run every gate. Returns a per-canon record whose
    ``status`` is ``"ok"`` only when the reading is grounded, entailed (audit
    sound), evidence- and warrant-clean, and at or above the confidence floor.

    A record always carries ``reading`` (the candidate, may be ``None``),
    ``span``, ``confidence``, ``audit`` (the verify verdict), ``closure`` (the
    audit closure — the wording-admissible set when this is the cap canon) and
    ``status``.
    """
    conf = _parse_conf(raw)
    interp = interpret_reasoning(raw)          # FILL: notation → structure
    reading = interp["candidate"]
    facts = interp["facts"]
    audit_rep = audit_reasoning(interp)        # VERIFY: is the reading entailed?

    rec = {
        "reading": reading,
        "span": "; ".join(sorted(facts)),
        "confidence": conf,
        "audit": audit_rep["verdict"],
        "closure": list(audit_rep["closure"]),
        "status": "ok",
        "detail": "",
    }

    # grounding + verify (interpret.audit): a reading with no span, or one the
    # span does not entail, is a leap — drop it.
    if reading is None or not facts:
        rec["status"] = "ungrounded"
        rec["detail"] = "no reading grounded to a span"
        return rec
    if audit_rep["verdict"] != "sound":
        rec["status"] = "unsound"
        rec["detail"] = "reading not entailed by its span (" + \
            "; ".join(audit_rep["reasons"]) + ")"
        return rec

    # a case-shaped record for the reasoning-contract gate functions.
    span = rec["span"]
    case = {
        "problem": {"text": element},
        "facts": [{"text": span, "source": f"{canon}:{span}"}],
        "grounds": [{"pinpoint": span, "receipted": True}],
        "chain": [{"step": "meaning",
                   "warrant": f"{canon} canon: {span} ⇒ {reading}"}],
    }
    ev = check_evidence(case)                   # evidence gate
    wr = check_warrants(case)                    # warrant gate
    cf = check_confidence({"solution": {"confidence": conf}},
                          risk_class=risk_class)  # confidence-floor gate

    if _has(ev, Level.VIOLATION) or _has(wr, Level.VIOLATION):
        rec["status"] = "malformed"
        rec["detail"] = "evidence/warrant violation"
    elif _has(cf, Level.VIOLATION):
        rec["status"] = "no-confidence"
        rec["detail"] = "no numeric confidence stated"
    elif _has(cf, Level.ESCALATE):
        rec["status"] = "sub-floor"
        rec["detail"] = "confidence below the contract floor"
    elif _has(wr, Level.ESCALATE):
        rec["status"] = "unwarranted"
        rec["detail"] = "interpretive move names no warrant"
    else:
        rec["status"] = "ok"
        rec["detail"] = "grounded, entailed, warranted, above floor"
    return rec


# ── the operation ────────────────────────────────────────────────────────────

def interpret_element(
    element: str,
    text: str,
    *,
    model: ModelFn,
    family: str = "civil-law",
    settled: Optional[str] = None,
    risk_class: str = "C",
) -> ReadingResult:
    """Interpret one ``element`` in its ``text`` via the canons of ``family``.

    Returns a grounded :class:`ReadingResult` OR an escalation — never a reading
    that crosses the wording cap and never an ungrounded one.

    ``model``     the injected :data:`ports.ModelFn` (never a real LLM here). It
                  proposes one reading per canon; the contract gates each.
    ``family``    a legal family or a registered synonym (``canons.canon_set_for``).
    ``settled``   O36: a pre-settled reading for the element. When given (truthy),
                  it is returned directly and the model is never called — an
                  unambiguous element needs no canons.
    ``risk_class`` fed to the confidence gate; ``"C"`` (the high-stakes class)
                  makes the floor bite. Confidence is necessary, never sufficient.
    """
    cs: CanonSet = canon_set_for(family)   # (a) SELECT the ordered canon set
    provenance = {
        "family": cs.family,
        "label": cs.label,
        "canons": list(cs.canons),
        "tiebreaker": cs.tiebreaker,
        "cap": cs.cap,
    }

    # (b) O36 — a settled reading short-circuits: no canons, no model call.
    if settled is not None and str(settled).strip():
        return ReadingResult(
            reading=str(settled),
            escalated=False,
            reason="element has a settled reading — no canons needed (O36)",
            canon_readings={},
            tiebreaker_used=False,
            gate_report={},
            provenance=provenance,
        )

    # (c) FILL + GATE each canon.
    canon_readings: dict[str, dict] = {}
    for canon in cs.canons:
        raw = model(canon_prompt(canon, element, text))
        canon_readings[canon] = _gate_canon(canon, element, raw,
                                             risk_class=risk_class)

    gate_report = {c: {"status": r["status"], "audit": r["audit"],
                       "confidence": r["confidence"], "detail": r["detail"]}
                   for c, r in canon_readings.items()}

    survivors = {c: r for c, r in canon_readings.items() if r["status"] == "ok"}

    def escalate(reason: str, *, tiebreaker_used: bool = False) -> ReadingResult:
        return ReadingResult(
            reading=None, escalated=True, reason=reason,
            canon_readings=canon_readings, tiebreaker_used=tiebreaker_used,
            gate_report=gate_report, provenance=provenance,
        )

    # No canon cleared the gates → escalate. Name the confidence floor when that
    # is why (confidence never trusted alone, but its absence is reportable).
    if not survivors:
        only_floor = canon_readings and all(
            r["status"] in ("sub-floor", "no-confidence")
            for r in canon_readings.values())
        reason = (
            "no canon reading cleared the confidence floor — escalate (O48)"
            if only_floor else
            "no canon produced a gated, grounded reading — escalate (O48)"
        )
        return escalate(reason)

    # (d) O43 — divergence across the surviving readings.
    distinct = {r["reading"] for r in survivors.values()}

    if len(distinct) == 1:
        # (e) O45 — converge: synthesise the single agreed reading.
        final_reading = next(iter(distinct))
        tiebreaker_used = False
        reason = "canons converge — synthesised reading (O45)"
    else:
        # (f) O44 — diverge: weight by the family's tie-breaker.
        tb = cs.tiebreaker
        if tb not in survivors:
            # (h) O48 — the tie-breaker canon produced no gated reading: the
            # family's own instrument for settling the tie is unavailable, so
            # the divergence is genuinely open.
            return escalate(
                f"canons diverge and the tie-breaker ({tb}) produced no gated "
                f"reading — the divergence is unsettled, escalate (O48)")
        final_reading = survivors[tb]["reading"]
        tiebreaker_used = True
        reason = f"canons diverge — tie broken by the {tb} canon (O44)"

    # (g) O37 — WORTLAUTGRENZE: the wording reading is the outer limit. A reading
    # the grammatical wording cannot bear is contra legem — escalate, never
    # return it. Where the tradition has no such cap, there is no limit to cross.
    if cs.cap:
        cap_rec = canon_readings.get(cs.cap)
        if cap_rec is None or cap_rec["status"] != "ok":
            # The wording bound could not itself be established — we cannot
            # certify the reading stays within it. Bound-unknown beats
            # bound-assumed: escalate.
            return escalate(
                f"the wording cap ({cs.cap}) produced no gated reading — the "
                f"Wortlautgrenze is unestablished, cannot certify the reading "
                f"stays within it, escalate (O37)",
                tiebreaker_used=tiebreaker_used)
        admissible = set(cap_rec["closure"])
        if final_reading not in admissible:
            return escalate(
                f"the reading {final_reading!r} crosses the grammatical cap "
                f"(Wortlautgrenze) — the wording cannot bear it, contra legem, "
                f"escalate (O37)",
                tiebreaker_used=tiebreaker_used)

    return ReadingResult(
        reading=final_reading,
        escalated=False,
        reason=reason,
        canon_readings=canon_readings,
        tiebreaker_used=tiebreaker_used,
        gate_report=gate_report,
        provenance=provenance,
    )
