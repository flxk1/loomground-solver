# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Structured condition predicates — the executable face of a rule condition.

``RuleFacet.condition`` keeps the verbatim source text (that is the legal
truth). This module adds the *optional* structured reading the obligation
runtime can evaluate against facts: a :class:`Predicate` with a kind, a
subject reference, a comparator, a typed value, and an optional temporal
component (``RelativeDeadline``).

Discipline (NT-12): a predicate is only attached when the deterministic
parser is confident (>= 0.85). Anything it cannot read cleanly stays
``None`` — verbatim text without a struct is honest; a guessed struct is a
contract violation. The parser is deliberately narrow: common deadline and
threshold phrasings in EN + DE. Phase-2 (LLM) may widen coverage later, but
its output passes through the same validation and the same floor.

Pure stdlib.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .temporal import Duration, Money, RelativeDeadline, TemporalError

__all__ = ["Predicate", "PredicateError", "parse_condition", "attach_predicates",
           "PREDICATE_CONFIDENCE_FLOOR"]

PREDICATE_CONFIDENCE_FLOOR = 0.85

_KINDS = ("event", "threshold", "state")
_COMPARATORS = ("<", "<=", ">", ">=", "==", "!=")


class PredicateError(ValueError):
    """Raised when a predicate is malformed. Reject, don't coerce."""


@dataclass(frozen=True)
class Predicate:
    """One evaluable condition. ``kind``:

    * ``event``     — something happens; deadline semantics via ``temporal``;
    * ``threshold`` — a quantity crosses a comparator (value + unit);
    * ``state``     — a boolean state of the subject holds.
    """

    kind: str
    subject_ref: str = ""                      # what the condition is about
    comparator: Optional[str] = None           # thresholds only
    value: Optional[str] = None                # stored as str (Decimal-safe)
    unit: Optional[str] = None                 # ISO 4217 code, "days", "%" …
    temporal: Optional[RelativeDeadline] = None
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in _KINDS:
            raise PredicateError(f"predicate kind must be one of {_KINDS}, got {self.kind!r}")
        if self.comparator is not None and self.comparator not in _COMPARATORS:
            raise PredicateError(f"comparator must be one of {_COMPARATORS}, got {self.comparator!r}")
        if self.kind == "threshold":
            if self.comparator is None or self.value is None:
                raise PredicateError("threshold predicate needs comparator + value")
            try:
                Decimal(self.value)
            except Exception as exc:           # noqa: BLE001
                raise PredicateError(f"threshold value must be decimal, got {self.value!r}") from exc
        if self.temporal is not None and not isinstance(self.temporal, RelativeDeadline):
            raise PredicateError("temporal must be a RelativeDeadline")
        if not isinstance(self.confidence, (int, float)) or not (0.0 <= self.confidence <= 1.0):
            raise PredicateError(f"confidence must be in [0,1], got {self.confidence!r}")

    def to_dict(self) -> dict:
        return {"kind": self.kind, "subject_ref": self.subject_ref,
                "comparator": self.comparator, "value": self.value,
                "unit": self.unit,
                "temporal": self.temporal.to_dict() if self.temporal else None,
                "confidence": self.confidence}

    @classmethod
    def from_dict(cls, d: dict) -> "Predicate":
        return cls(kind=d["kind"], subject_ref=d.get("subject_ref", ""),
                   comparator=d.get("comparator"), value=d.get("value"),
                   unit=d.get("unit"),
                   temporal=RelativeDeadline.from_dict(d["temporal"]) if d.get("temporal") else None,
                   confidence=d.get("confidence", 0.0))


# ── deterministic Phase-1 parser ──────────────────────────────────────────────
# Narrow on purpose. Each pattern yields a high-confidence reading or nothing.

_UNIT_TO_DURATION = {
    "day": "P{n}D", "days": "P{n}D", "tag": "P{n}D", "tagen": "P{n}D", "tage": "P{n}D",
    "week": "P{n}W", "weeks": "P{n}W", "woche": "P{n}W", "wochen": "P{n}W",
    "month": "P{n}M", "months": "P{n}M", "monat": "P{n}M", "monaten": "P{n}M", "monate": "P{n}M",
    "year": "P{n}Y", "years": "P{n}Y", "jahr": "P{n}Y", "jahren": "P{n}Y", "jahre": "P{n}Y",
    "hour": "PT{n}H", "hours": "PT{n}H", "stunde": "PT{n}H", "stunden": "PT{n}H",
}

# EN: "within 30 days of/after/following the signing" · "no later than 72 hours after X"
_EN_DEADLINE = re.compile(
    r"\b(?:within|no later than|not later than|at the latest)\s+"
    r"(?P<n>\d+)\s+(?P<unit>day|days|week|weeks|month|months|year|years|hour|hours)\s+"
    r"(?:of|after|following|from)\s+(?:the\s+)?(?P<event>[a-z][a-z0-9 _-]{2,60}?)"
    r"(?:[,;.]|$)", re.I)

# DE: "innerhalb von 30 Tagen nach Vertragsschluss" · "spätestens 72 Stunden nach X"
_DE_DEADLINE = re.compile(
    r"\b(?:innerhalb\s+von|spätestens|binnen)\s+"
    r"(?P<n>\d+)\s+(?P<unit>Tag|Tagen|Tage|Woche|Wochen|Monat|Monaten|Monate|Jahr|Jahren|Jahre|Stunde|Stunden)\s+"
    r"(?:nach|ab)\s+(?:dem\s+|der\s+)?(?P<event>[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß _-]{2,60}?)"
    r"(?:[,;.]|$)")

# EN/DE threshold: "exceeds EUR 10,000" · "of at least 500 EUR" · "über 10.000 EUR"
_THRESHOLD = re.compile(
    r"\b(?P<cmp>exceed(?:s|ing)?|more than|at least|at most|less than|über|mindestens|höchstens|unter)\s+"
    r"(?:(?P<cur1>[A-Z]{3})\s*)?(?P<amount>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)(?:\s*(?P<cur2>[A-Z]{3}|%))?",
    re.I)

_CMP_MAP = {
    "exceed": ">", "exceeds": ">", "exceeding": ">", "more than": ">", "über": ">",
    "at least": ">=", "mindestens": ">=",
    "at most": "<=", "höchstens": "<=",
    "less than": "<", "unter": "<",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


def _normalise_amount(raw: str) -> Optional[str]:
    """'10.000,50' / '10,000.50' / '500' → canonical decimal string, or None
    when the grouping is ambiguous (ambiguity = abstain, not guess)."""
    s = raw.strip()
    if "," in s and "." in s:
        # last separator wins as decimal point
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        if len(tail) == 3 and head:          # 10,000 → grouping
            s = s.replace(",", "")
        else:                                # 10,50 → decimal
            s = s.replace(",", ".")
    elif "." in s:
        head, _, tail = s.rpartition(".")
        if len(tail) == 3 and head:          # 10.000 → grouping (EU)
            s = s.replace(".", "")
    try:
        Decimal(s)
        return s
    except Exception:                        # noqa: BLE001
        return None


def parse_condition(text: str, language: str = "en") -> Optional[Predicate]:
    """Deterministic predicate parse of one condition string. Returns a
    Predicate with confidence >= the floor, or None (abstain). Never raises
    on unparseable input — unparseable means None."""
    if not text or not text.strip():
        return None
    t = re.sub(r"\s+", " ", text).strip()      # source text wraps lines

    for rx in (_EN_DEADLINE, _DE_DEADLINE):
        m = rx.search(t)
        if m:
            unit = m["unit"].lower()
            iso = _UNIT_TO_DURATION.get(unit)
            if iso is None:
                continue
            try:
                rd = RelativeDeadline(event=_slug(m["event"]),
                                      offset=Duration.parse(iso.format(n=int(m["n"]))),
                                      direction="after")
            except TemporalError:
                return None
            return Predicate(kind="event", subject_ref=_slug(m["event"]),
                             temporal=rd, confidence=0.9)

    m = _THRESHOLD.search(t)
    if m:
        cmp_word = m["cmp"].lower()
        comparator = _CMP_MAP.get(cmp_word)
        amount = _normalise_amount(m["amount"])
        # "unpaid for more than 30 days" is elapsed time, not money — a time
        # word in unit position (or captured AS the unit: "day" is 3 letters
        # and fools the [A-Z]{3} currency shape) means no monetary threshold.
        _TIME_WORDS = ("day", "week", "month", "year", "hour",
                       "tag", "woche", "monat", "jahr", "stunde")
        tail = t[m.end():m.end() + 12].strip().lower()
        cur2 = (m["cur2"] or "").lower()
        if (any(tail.startswith(w) for w in _TIME_WORDS)
                or any(cur2.startswith(w) for w in _TIME_WORDS)):
            comparator = None                      # abstain, not misread
        if comparator and amount is not None:
            unit = (m["cur1"] or m["cur2"] or "").upper() or None
            if unit and unit != "%":
                try:
                    Money(amount=Decimal(amount), currency=unit)
                except TemporalError:
                    unit = None              # malformed currency → keep amount, drop unit
            return Predicate(kind="threshold", subject_ref="amount",
                             comparator=comparator, value=amount, unit=unit,
                             confidence=0.88)
    return None


def attach_predicates(facets: list, language: str = "en") -> int:
    """Opt-in pass over extracted RuleFacets: fill ``condition_struct`` where
    the parser is confident; leave None otherwise. Returns the number filled.
    Mutates the facets in place (the dataclass field exists; this populates it).

    Parses the full ``raw_sentence`` first — Phase-1's ``condition`` slot can
    be truncated at clause punctuation ("…exceeds EUR 50" from "EUR 50,000"),
    and deadline phrasings often sit in the action, not the condition. The
    verbatim sentence is the superset; the narrow parser keeps it safe."""
    n = 0
    for f in facets:
        if getattr(f, "condition_struct", None) is not None:
            continue
        lang = getattr(f, "language", language)
        p = None
        for candidate in (getattr(f, "raw_sentence", "") or "",
                          getattr(f, "condition", "") or ""):
            if candidate:
                p = parse_condition(candidate, language=lang)
                if p is not None:
                    break
        if p is not None and p.confidence >= PREDICATE_CONFIDENCE_FLOOR:
            f.condition_struct = p.to_dict()
            n += 1
    return n
