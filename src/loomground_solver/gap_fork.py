# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Gap fork — a *Rechtsfortbildung* fork: given a norm-text and an issue it does
not literally reach, resolve the **gap** honestly, or escalate. An [I]-tier op:
the **model fills** (classifies the gap and proposes the resolution move), the
**contract gates**, the harness **escalates** the open.

A rule reasons over what its wording covers (subsume → apply). Beyond the
wording lies the gap (*Lücke*), and how a gap is filled is not a decision to be
guessed — it is a *methodenehrliche* move that must be justified. This module is
the door for that move, and it is deliberately not a decider: a model proposes a
**gap classification** and a **resolution move**, each element **tagged with the
source span it was drawn from** and a confidence, and a chain of **deterministic
gates** decides whether the move may stand.

It wraps what exists rather than regrowing it:

  * the fill is the injected :data:`ports.ModelFn` (``str -> str``): the package
    never binds a model; the completion is a JSON proposal it decodes;
  * an **analogy** is carried by the existing analogy primitive,
    :func:`methods.inference.analogical_inference` — relational structure is
    transferred from the like-case to the gap-case through it, never
    reimplemented here;
  * coherence of the move is verified through :func:`interpret.interpret` (the
    fill seam) and :func:`interpret.audit` (the solver catching a self-
    contradictory or unwarranted resolution);
  * the confidence floor is the existing contract,
    :func:`norm_contract.check_confidence` / :data:`norm_contract.CONFIDENCE_FLOOR`.

The gap-honesty floor is committed, not optional:

  1. **grounding** — every proposed span must be a *substring of the material*
     (the norm-text and the issue). An element whose span is not found is
     REJECTED as invented. No ungrounded move is ever returned.
  2. **planned gap → e_contrario (NOT_MET)** — a deliberate legislative silence
     (*beredtes Schweigen*) is not filled; the inverse conclusion is drawn and
     the norm does NOT reach the case.
  3. **planwidrig gap → analogy-eligible** — only a plan-contradictory gap
     (*planwidrige Unvollständigkeit*) may be closed by a gap-filling move
     (analogy, a-fortiori, teleological extension/reduction).
  4. **Wortlautgrenze** — an extension/analogy that would cross the outer limit
     of the wording into *contra legem* is the legislature's job: it ESCALATES,
     never returns. A closed/exhaustive enumeration in the wording is that limit.
  5. **ambiguous classification ESCALATES** — a gap the model cannot place as
     planned XOR planwidrig is a human's call.
  6. **confidence is never trusted alone** — a high self-reported score cannot
     buy a move past thin grounding, a class/move mismatch or an unsound audit.

Pure stdlib (``json``, ``re``, ``dataclasses``, ``typing``). No governance, no
corpus, no domain: :func:`resolve_gap` takes a generic norm-text ``str`` and a
generic issue ``str`` — never a corpus-coupled provision or a real model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from . import norm_contract
from .interpret import audit as _audit_interp
from .interpret import interpret as _interpret
from .methods.inference import analogical_inference
from .norm_contract import CONFIDENCE_FLOOR, Level
from .ports import ModelFn
from .subsumption import Rule


# ── the move / class vocabularies (closed) ────────────────────────────────────

#: The six recognised gap-resolution moves.
MOVES = frozenset({
    "e_contrario",
    "analogy",
    "a_fortiori_maiore_minus",
    "a_fortiori_minori_maius",
    "teleological_reduction",
    "teleological_extension",
})

#: The two recognised gap classifications.
GAP_CLASSES = frozenset({"planned", "planwidrig"})

#: Moves that *extend* the norm beyond its wording — the ones the Wortlautgrenze
#: bounds. ``teleological_reduction`` narrows (it never extends), so it is not
#: here; ``e_contrario`` draws the inverse and reaches nothing to extend.
EXTENSION_MOVES = frozenset({
    "analogy",
    "a_fortiori_maiore_minus",
    "a_fortiori_minori_maius",
    "teleological_extension",
})

#: Moves that, once justified, extend the consequence to REACH the gap-case.
MET_MOVES = frozenset({
    "analogy",
    "a_fortiori_maiore_minus",
    "a_fortiori_minori_maius",
    "teleological_extension",
})

#: Moves that resolve the gap by NOT reaching the case (inverse / cut-back).
NOT_MET_MOVES = frozenset({"e_contrario", "teleological_reduction"})

#: Outcome tokens (aligned with grading.Terminal / subsumption's not-met sense).
MET = "MET"
NOT_MET = "NOT_MET"

# The wording's outer limit: a closed / exhaustive / exclusive enumeration. Its
# presence marks the wording as a cap an extension may not cross (contra legem).
_WORTLAUT_CAP = re.compile(
    r"\b(?:only|solely|exclusively|exhaustively|and no other|no other(?:s)?|"
    r"nur|ausschließlich|abschließend|erschöpfend|einzig|keine\s+(?:andere|weitere))\b",
    re.I,
)


# ── the proposal schema the ModelFn returns ───────────────────────────────────

@dataclass(frozen=True)
class Element:
    """One span-tagged piece of the proposal: the verbatim ``span`` it was drawn
    from, a solver ``literal``, the model's ``confidence`` and its ``role``."""

    span: str
    literal: str
    confidence: float = 1.0
    role: str = "gap"

    @classmethod
    def from_dict(cls, d: dict, *, role: str = "gap") -> "Element":
        return cls(span=str(d.get("span", "")),
                   literal=str(d.get("literal", "")),
                   confidence=float(d.get("confidence", 1.0)),
                   role=str(d.get("role", role)))

    def grounded_in(self, haystack: str) -> bool:
        """Gap-honesty floor #1: the span must be a substring of the material."""
        return bool(self.span) and self.span in haystack

    def receipt(self, haystack: str) -> dict[str, Any]:
        start = haystack.find(self.span) if self.span else -1
        end = start + len(self.span) if start >= 0 else -1
        return {"role": self.role, "literal": self.literal, "span": self.span,
                "start": start, "end": end, "confidence": self.confidence,
                "grounded": start >= 0}


@dataclass(frozen=True)
class GapProposal:
    """A model's proposed classification and resolution of a gap. Convention,
    not truth — every field faces the gates before any of it may stand."""

    gap_class: str = ""                       # planned | planwidrig
    move: str = ""                            # one of MOVES
    gap: Optional[Element] = None             # the span evidencing the gap
    like_case: Optional[Element] = None       # analogy: the regulated like-case
    relevant_similarity: Optional[Element] = None  # analogy: the tertium comparationis
    result_literal: str = ""                  # what the resolution asserts reaches / not
    # the structural payload the analogy primitive transfers:
    analogy_mapping: dict = field(default_factory=dict)          # a -> a'
    analogy_source_relations: tuple = ()      # (a, rel, b) triples from the like-case
    contra_legem: bool = False                # model self-report of a wording-crossing

    @classmethod
    def from_dict(cls, d: dict) -> "GapProposal":
        def _el(key, role):
            v = d.get(key)
            return Element.from_dict(v, role=role) if v else None
        rels = tuple(tuple(t) for t in (d.get("analogy_source_relations") or ()))
        return cls(
            gap_class=str(d.get("gap_class", "")).strip().lower(),
            move=str(d.get("move", "")).strip().lower(),
            gap=_el("gap", "gap"),
            like_case=_el("like_case", "like_case"),
            relevant_similarity=_el("relevant_similarity", "relevant_similarity"),
            result_literal=str(d.get("result_literal", "")),
            analogy_mapping=dict(d.get("analogy_mapping") or {}),
            analogy_source_relations=rels,
            contra_legem=bool(d.get("contra_legem", False)),
        )

    @classmethod
    def from_json(cls, raw: str) -> "GapProposal":
        return cls.from_dict(json.loads(raw))

    def all_elements(self) -> list[Element]:
        return [e for e in (self.gap, self.like_case, self.relevant_similarity)
                if e is not None]

    def min_confidence(self) -> float:
        confs = [e.confidence for e in self.all_elements()]
        return min(confs) if confs else 0.0


# ── the model port: a deterministic stub for tests ────────────────────────────

class StubModel:
    """A deterministic :data:`ports.ModelFn` (``str -> str``): it ignores the
    prompt and returns a *fixed* canned proposal as JSON. Faithful to the real
    seam — a host's model likewise returns a completion string that
    :func:`resolve_gap` decodes — but with no model runtime, so the gates are
    exercised deterministically."""

    def __init__(self, proposal: dict):
        self._payload = json.dumps(proposal)

    def __call__(self, prompt: str) -> str:   # ports.ModelFn
        return self._payload


def _build_prompt(text: str, issue: str) -> str:
    """The instruction handed to the model. Content is irrelevant to the gates
    (a real model reads it; :class:`StubModel` ignores it) — but the call is a
    genuine ``ModelFn`` invocation, so the seam is consumed, not bypassed."""
    return ("A norm-text and an issue it does not literally reach follow. "
            "Classify the gap (planned | planwidrig), choose a resolution move "
            f"({', '.join(sorted(MOVES))}), and for an analogy give the like-case "
            "and the relevant similarity. Tag every element with its verbatim "
            "source SPAN and a confidence. Reply as JSON.\n\n"
            f"NORM:\n{text}\n\nISSUE:\n{issue}\n")


# ── the result ────────────────────────────────────────────────────────────────

@dataclass
class GapResult:
    """The outcome of a gap-resolution attempt. It carries a resolved move XOR an
    escalation/rejection — never an ungrounded or contra-legem move."""

    status: str                                  # resolved | not_met | rejected | escalated
    move: str
    outcome: str                                 # MET | NOT_MET | ""
    like_case: str = ""
    escalated: bool = False
    reason: str = ""
    gate_report: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def resolved(self) -> bool:
        return self.status in ("resolved", "not_met")

    @property
    def rejected(self) -> bool:
        return self.status == "rejected"


def _reject(reason, move, report, prov) -> GapResult:
    return GapResult("rejected", move, "", "", False, reason, report, prov)


def _escalate(reason, move, report, prov, like_case="") -> GapResult:
    return GapResult("escalated", move, "", like_case, True, reason, report, prov)


# ── the reasoning-audit bridge (consumes interpret.interpret + interpret.audit)─

def _audit_move(text: str, proposal: GapProposal, *, met: bool) -> dict:
    """Cast the move as facts + (a rule) + a candidate so the existing auditor
    can check it. For a REACH move the relevant-similarity licenses the result
    (``similarity => result``); a self-contradictory premise set comes back
    inconsistent, a result the premises cannot reach comes back unwarranted. For
    a NOT-reach move only the grounds' consistency is checked (no candidate)."""
    premises = []
    for e in (proposal.relevant_similarity, proposal.like_case, proposal.gap):
        if e is not None and e.literal:
            premises.append(e.literal)
    if met and proposal.result_literal:
        conds = tuple(p for p in (proposal.relevant_similarity and
                                  proposal.relevant_similarity.literal,) if p)
        rule = Rule(id="gap", conditions=conds or tuple(premises),
                    consequence=proposal.result_literal)
        interp_payload = {"facts": set(premises), "rules": [rule],
                          "candidate": proposal.result_literal}
    else:
        interp_payload = {"facts": set(premises), "rules": [], "candidate": None}
    interp = _interpret(text, parse=lambda _t: interp_payload)
    return _audit_interp(interp)


def _confidence_finding(min_conf: float, risk_class: str):
    """NT-9 via :func:`norm_contract.check_confidence` — the confidence floor is
    consumed, not reimplemented."""
    pair = {"id": "gap", "solution": {"confidence": min_conf}}
    return norm_contract.check_confidence(pair, risk_class=risk_class)


def _has_escalate(findings) -> bool:
    return any(f.level is Level.ESCALATE for f in findings)


# ── the op ────────────────────────────────────────────────────────────────────

def resolve_gap(
    text: str,
    issue: str,
    *,
    model: ModelFn,
    risk_class: str = "C",
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> GapResult:
    """Resolve the gap between ``text`` and ``issue``, or escalate.

    The ``model`` (an injected :data:`ports.ModelFn`) proposes a gap
    classification and a resolution move; deterministic gates then decide. The
    gates, in order of precedence:

      * **grounding** — any element whose span is not a substring of the
        material (``text`` + ``issue``) is invented → REJECT;
      * **vocabulary** — an unknown move → REJECT (malformed);
      * **ambiguous class** — a class that is not planned XOR planwidrig →
        ESCALATE;
      * **Wortlautgrenze** — an extension/analogy over a wording that carries a
        closed/exhaustive enumeration (or a model-flagged crossing) is
        *contra legem* → ESCALATE, never returned;
      * **class routing** — a planned gap admits only ``e_contrario`` (→
        NOT_MET); a planwidrig gap admits only the gap-filling moves; a
        class/move mismatch → ESCALATE;
      * **analogy transfer** — for ``analogy``, the relational structure is
        carried by :func:`methods.inference.analogical_inference`; a transfer
        that carries nothing → ESCALATE;
      * **audit** — :func:`interpret.audit` must find the move coherent; an
        inconsistent or unwarranted resolution → ESCALATE;
      * **confidence floor** — NT-9 / :data:`CONFIDENCE_FLOOR`; sub-floor →
        ESCALATE regardless of any single high score.

    A planned gap resolved by ``e_contrario`` returns status ``not_met`` with
    outcome ``NOT_MET`` — a determinate negative, a pass. A planwidrig gap
    closed by a grounded, audited, at/above-floor move returns status
    ``resolved`` with outcome ``MET`` (reach) or ``NOT_MET`` (teleological
    reduction). Everything else is a rejection or an escalation.
    """
    haystack = (text or "") + "\n" + (issue or "")
    prov: dict[str, Any] = {"issue": issue, "receipts": []}
    report: dict[str, Any] = {}

    # 0. Fill: consume the ModelFn seam and decode the proposal.
    raw = model(_build_prompt(text, issue))
    try:
        proposal = GapProposal.from_json(raw) if isinstance(raw, str) \
            else GapProposal.from_dict(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        report["decode"] = {"ok": False, "error": str(exc)}
        return _reject("model returned an undecodable proposal", "", report, prov)

    move = proposal.move
    prov["receipts"] = [e.receipt(haystack) for e in proposal.all_elements()]
    prov["move"], prov["gap_class"] = move, proposal.gap_class
    like_span = proposal.like_case.span if proposal.like_case else ""

    # 1. Grounding (gap-honesty floor #1): reject any invented span.
    invented = [e.span for e in proposal.all_elements() if not e.grounded_in(haystack)]
    report["grounding"] = {"ok": not invented, "invented": invented}
    if invented:
        return _reject(
            f"ungrounded element(s) — span not found in material: {invented!r}",
            move, report, prov)

    # 2. Vocabulary: an unknown move is malformed.
    report["vocabulary"] = {"move_ok": move in MOVES,
                            "class_ok": proposal.gap_class in GAP_CLASSES}
    if move not in MOVES:
        return _reject(f"unknown move {move!r} (closed vocabulary: {sorted(MOVES)})",
                       move, report, prov)

    # 3. Ambiguous classification → ESCALATE (a human places the gap).
    if proposal.gap_class not in GAP_CLASSES:
        return _escalate(
            f"gap class {proposal.gap_class!r} is not planned XOR planwidrig — "
            "the classification is ambiguous, escalate", move, report, prov, like_span)

    # 4. WORTLAUTGRENZE: an extension over a closed wording (or a flagged
    #    crossing) is contra legem — the legislature's job, never returned.
    cap_hit = _WORTLAUT_CAP.search(text or "")
    crosses = (move in EXTENSION_MOVES and cap_hit is not None) or proposal.contra_legem
    report["wortlautgrenze"] = {
        "extension": move in EXTENSION_MOVES,
        "wording_cap": cap_hit.group(0) if cap_hit else "",
        "contra_legem_flag": proposal.contra_legem,
        "crosses": crosses,
    }
    if crosses:
        why = (f"the wording carries a closed enumeration ({cap_hit.group(0)!r})"
               if cap_hit else "the move is flagged contra legem")
        return _escalate(
            f"Wortlautgrenze — {why}; extending the norm here is contra legem, a "
            "legislature's job, escalate", move, report, prov, like_span)

    # 5. Class routing: planned → e_contrario only; planwidrig → gap-filling only.
    planned = proposal.gap_class == "planned"
    if planned and move != "e_contrario":
        return _escalate(
            "planned gap (beredtes Schweigen) admits only e_contrario; the "
            f"proposed {move!r} would fill a deliberate silence — escalate",
            move, report, prov, like_span)
    if (not planned) and move == "e_contrario":
        return _escalate(
            "planwidrig gap does not license an inverse conclusion; e_contrario "
            "contradicts the classification — escalate", move, report, prov, like_span)
    report["routing"] = {"gap_class": proposal.gap_class, "move": move, "ok": True}

    # 6. Analogy: consume the analogy primitive to transfer relational structure
    #    from the like-case to the gap-case. Reimplemented nowhere.
    if move == "analogy":
        if proposal.like_case is None or proposal.relevant_similarity is None:
            return _escalate(
                "analogy without a like-case and a relevant similarity — the "
                "tertium comparationis is a human's to supply, escalate",
                move, report, prov, like_span)
        transferred = analogical_inference(
            set(),
            mapping=proposal.analogy_mapping,
            source_relations=proposal.analogy_source_relations,
        )["facts"]
        report["analogy"] = {
            "mapping": proposal.analogy_mapping,
            "source_relations": [list(t) for t in proposal.analogy_source_relations],
            "transferred": transferred,
            "carried": bool(transferred),
        }
        prov["analogy_transferred"] = transferred
        if not transferred:
            return _escalate(
                "analogical_inference carried no structure — the mapping does not "
                "align the like-case onto the gap-case, escalate",
                move, report, prov, like_span)

    met = move in MET_MOVES

    # 7. Audit: consume interpret.interpret + interpret.audit.
    audit_report = _audit_move(text, proposal, met=met)
    audited = audit_report["verdict"] == "sound"
    report["audit"] = {"verdict": audit_report["verdict"],
                       "reasons": audit_report["reasons"]}
    if not audited:
        return _escalate("audit unsound — " + "; ".join(audit_report["reasons"]),
                         move, report, prov, like_span)

    # 8. Confidence floor: NT-9 plus a hard floor (never trusted alone).
    min_conf = proposal.min_confidence()
    nt9 = _confidence_finding(min_conf, risk_class)
    sub_floor = min_conf < confidence_floor or _has_escalate(nt9)
    report["confidence"] = {"min": min_conf, "floor": confidence_floor,
                            "ok": not sub_floor, "nt9": [f.to_dict() for f in nt9]}
    if sub_floor:
        return _escalate(
            f"sub-floor confidence {min_conf} < {confidence_floor}", move,
            report, prov, like_span)

    # 9. Resolve. planned/e_contrario and teleological_reduction do NOT reach the
    #    case (NOT_MET, a determinate negative); the extension moves reach it (MET).
    outcome = MET if met else NOT_MET
    status = "not_met" if outcome == NOT_MET else "resolved"
    report["resolved"] = {"outcome": outcome, "move": move}
    reason = {
        "e_contrario": "planned gap — inverse conclusion, the norm does not reach the case",
        "teleological_reduction": "planwidrig gap — purpose reduces the over-broad wording, "
                                  "the case is carved out",
        "analogy": "planwidrig gap — like-case structure transferred by analogy, "
                   "the consequence reaches the case",
        "a_fortiori_maiore_minus": "planwidrig gap — a fortiori (from the greater to the "
                                   "lesser), the consequence reaches the case",
        "a_fortiori_minori_maius": "planwidrig gap — a fortiori (from the lesser to the "
                                   "greater), the consequence reaches the case",
        "teleological_extension": "planwidrig gap — purpose extends the wording, the "
                                  "consequence reaches the case",
    }.get(move, "gap resolved")
    return GapResult(status, move, outcome, like_span, False, reason, report, prov)
