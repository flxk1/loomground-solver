# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Norm-theory contract for legal NDs — the enforceable floor.

A norm ND (see :mod:`workspaces.domain_nds`) emits *pairs* — but the pair shape is
convention, not guarantee. This module turns the norm-theoretic requirements
(the legal-RAG register) into **invariants a pair must satisfy
before it is allowed to stand**, so "the rules are sure" is enforced at
emission rather than hoped for downstream.

The contract is deliberately split into three verdicts, never two:

    PASS       — the invariant holds.
    VIOLATION  — the emission is malformed (missing provenance, a guessed date,
                 a dropped exception). The gate REJECTS it.
    ESCALATE   — the emission is well-formed but the law itself hands the call
                 to a human: discretion (kann/soll/Härtefall), a genuine norm
                 collision, an unknown validity date, or sub-floor confidence.

Two hard lines this module will not cross, by rule:

  * It never *infers* a date. A temporal status must be sourced (registry) or
    declared ``unknown`` (NT-2 / NT-10). A model-supplied date is a VIOLATION.
  * It never *resolves* a norm collision. lex specialis / posterior / superior
    may be *recorded* as stated, provenance-bound relations, but the contract
    forbids deriving a winner from them — a genuine conflict ESCALATES (NT-6).
    The one exception: lex posterior may be *applied* only through a
    registry-dated supersession (deterministic, date-backed), never inferred.

Pure module: stdlib only, operates on plain dicts. No mcp, no I/O — so it is
unit-testable and can run inside ``NDRouter.dispatch`` or a CI gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional


from .predicate import PREDICATE_CONFIDENCE_FLOOR
# One floor for the whole package. Defined once in the leaf module `predicate`
# (which imports nothing from here, so no cycle) and aliased here as the canonical
# name every [I]-tier harness consumes — `norm_contract.CONFIDENCE_FLOOR`. No second
# 0.85 literal to drift.
CONFIDENCE_FLOOR = PREDICATE_CONFIDENCE_FLOOR

# Discretionary modality — its presence forbids an autonomous decision (NT-4).
DISCRETION_MODALS = {"kann", "soll", "may", "should", "discretion", "ermessen"}

# Exception phrasing the rule body must not silently absorb (NT-5).
_EXCEPTION_MARKERS = re.compile(
    r"\b(?:es sei denn|abweichend|unbeschadet|soweit|in besonderen|"
    r"kann abgesehen werden|unless|by way of derogation|notwithstanding|save where)\b",
    re.I,
)

# A date that looks asserted in free text (used to catch a model-guessed date
# living somewhere it should not — NT-2).
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

# Recognised stated meta-relations. Carried as provenance, never auto-resolved.
_META_RELATIONS = {"lex-specialis-to", "amends", "repeals", "supersedes",
                   "without-prejudice", "complements", "in-accordance-with"}


class Level(str, Enum):
    PASS = "pass"
    VIOLATION = "violation"
    ESCALATE = "escalate"


@dataclass
class Finding:
    level: Level
    code: str              # NT-1 .. NT-10
    message: str
    field: str = ""        # the offending field path, for an auditable "why"
    pair_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level.value, "code": self.code,
                "message": self.message, "field": self.field, "pair_id": self.pair_id}


@dataclass
class ContractReport:
    findings: list[Finding] = field(default_factory=list)

    @property
    def violations(self) -> list[Finding]:
        return [f for f in self.findings if f.level is Level.VIOLATION]

    @property
    def escalations(self) -> list[Finding]:
        return [f for f in self.findings if f.level is Level.ESCALATE]

    @property
    def ok(self) -> bool:
        """Conforming = no VIOLATION. Escalations are conforming-but-deferred."""
        return not self.violations

    @property
    def must_escalate(self) -> bool:
        return bool(self.escalations)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "must_escalate": self.must_escalate,
                "findings": [f.to_dict() for f in self.findings]}


# --- accessors (tolerant of absence; absence is what we are checking for) ----

def _facets(pair: dict) -> dict:
    return (pair.get("problem") or {}).get("facets") or {}


def _solution(pair: dict) -> dict:
    return pair.get("solution") or {}


def _edges(pair: dict) -> list[dict]:
    return pair.get("edges") or []


def _pid(pair: dict) -> str:
    return str(pair.get("id", ""))


# --- the invariants ----------------------------------------------------------
# Each returns zero or more Findings. A clean invariant emits one PASS so the
# report is a positive audit record, not only a list of failures.

def check_provenance(pair: dict) -> list[Finding]:
    """NT-1 Quellenbindung: every norm pair cites its source. No atom floats."""
    sol = _solution(pair)
    src = sol.get("source") or sol.get("citation") or pair.get("source_document")
    if not src:
        return [Finding(Level.VIOLATION, "NT-1", "no source/citation on pair", "solution.source", _pid(pair))]
    return [Finding(Level.PASS, "NT-1", "source bound", "solution.source", _pid(pair))]


def check_temporal(pair: dict) -> list[Finding]:
    """NT-2 Geltung: in-force status must be registry-sourced or 'unknown';
    a model-supplied date is a VIOLATION; 'unknown' ESCALATES (NT-10)."""
    sol = _solution(pair)
    temporal = sol.get("temporal") or {}
    if not temporal:
        return [Finding(Level.VIOLATION, "NT-2", "no temporal block (Geltung undeclared)", "solution.temporal", _pid(pair))]
    status = temporal.get("status")
    date_source = temporal.get("date_source")
    out: list[Finding] = []
    if status not in {"in-force", "not-yet-in-force", "superseded", "unknown"}:
        out.append(Finding(Level.VIOLATION, "NT-2", f"invalid temporal status {status!r}", "solution.temporal.status", _pid(pair)))
        return out
    # A concrete date present but not attributed to the registry = a guess.
    has_date = any(_DATE_RE.search(str(v)) for k, v in temporal.items() if k != "date_source")
    if has_date and date_source != "registry":
        out.append(Finding(Level.VIOLATION, "NT-2", "date present but date_source != 'registry' (guessed date)", "solution.temporal.date_source", _pid(pair)))
    if status == "unknown":
        out.append(Finding(Level.ESCALATE, "NT-2", "validity unknown — escalate, do not assume current", "solution.temporal.status", _pid(pair)))
    if not out:
        out.append(Finding(Level.PASS, "NT-2", f"temporal status {status} (registry-sourced)", "solution.temporal", _pid(pair)))
    return out


def check_applicability(pair: dict) -> list[Finding]:
    """NT-3 ratione materiae/personae: trigger projected to facets, or the pair
    explicitly marked broad ('unscoped'). A missing applicability block is a
    VIOLATION (silent over/under-inclusion is forbidden)."""
    f = _facets(pair)
    if "applicability" not in f:
        return [Finding(Level.VIOLATION, "NT-3", "no applicability facet projection", "problem.facets.applicability", _pid(pair))]
    return [Finding(Level.PASS, "NT-3", "applicability projected", "problem.facets.applicability", _pid(pair))]


def check_deontic(pair: dict) -> list[Finding]:
    """NT-4 rule theory: a rule must carry a deontic operator; discretionary
    modality (kann/soll/Härtefall) ESCALATES — the contract may not decide it."""
    f = _facets(pair)
    if (pair.get("problem") or {}).get("type") != "rule":
        return [Finding(Level.PASS, "NT-4", "non-rule pair; deontic n/a", "problem.type", _pid(pair))]
    modal = (f.get("modal") or "").strip().lower()
    if not modal:
        return [Finding(Level.VIOLATION, "NT-4", "rule pair without deontic operator", "problem.facets.modal", _pid(pair))]
    phrase = (f.get("modal_phrase") or "").lower()
    if modal in DISCRETION_MODALS or any(m in phrase for m in DISCRETION_MODALS):
        return [Finding(Level.ESCALATE, "NT-4", f"discretionary modality ({modal}) — human Ermessen required", "problem.facets.modal", _pid(pair))]
    return [Finding(Level.PASS, "NT-4", f"deontic operator {modal}", "problem.facets.modal", _pid(pair))]


def check_exception(pair: dict) -> list[Finding]:
    """NT-5 Ausnahme: if the source body contains exception phrasing, the pair
    must flag it (has_exception). An absorbed, unmarked exception is a VIOLATION."""
    f = _facets(pair)
    body = str(_solution(pair).get("body") or "")
    looks_exceptional = bool(_EXCEPTION_MARKERS.search(body))
    flagged = bool(f.get("has_exception"))
    if looks_exceptional and not flagged:
        return [Finding(Level.VIOLATION, "NT-5", "exception phrasing in body but has_exception not set", "problem.facets.has_exception", _pid(pair))]
    return [Finding(Level.PASS, "NT-5", "exceptions accounted for", "problem.facets.has_exception", _pid(pair))]


def check_authority(pair: dict) -> list[Finding]:
    """NT-7 Quellenhierarchie: every pair carries an authority_tier (int)."""
    tier = _solution(pair).get("authority_tier")
    if not isinstance(tier, int):
        return [Finding(Level.VIOLATION, "NT-7", "no integer authority_tier", "solution.authority_tier", _pid(pair))]
    return [Finding(Level.PASS, "NT-7", f"authority_tier {tier}", "solution.authority_tier", _pid(pair))]


def check_jurisdiction(pair: dict) -> list[Finding]:
    """NT-8 ratione loci: a norm pair carries >=1 jurisdiction anchor, or the
    explicit literal 'unscoped'. Absence is a VIOLATION (no silent scope)."""
    f = _facets(pair)
    j = f.get("jurisdiction")
    if j is None:
        return [Finding(Level.VIOLATION, "NT-8", "no jurisdiction anchor", "problem.facets.jurisdiction", _pid(pair))]
    if j == "unscoped" or (isinstance(j, (list, tuple)) and len(j) >= 1):
        return [Finding(Level.PASS, "NT-8", "jurisdiction scoped", "problem.facets.jurisdiction", _pid(pair))]
    return [Finding(Level.VIOLATION, "NT-8", "jurisdiction anchor empty", "problem.facets.jurisdiction", _pid(pair))]


def check_confidence(pair: dict, *, risk_class: str = "B") -> list[Finding]:
    """NT-9 confidence floor: on a class-C (Verwaltungsakt) context, sub-floor
    confidence ESCALATES rather than answers."""
    conf = _solution(pair).get("confidence")
    if not isinstance(conf, (int, float)):
        return [Finding(Level.VIOLATION, "NT-9", "no numeric confidence", "solution.confidence", _pid(pair))]
    if risk_class == "C" and conf < CONFIDENCE_FLOOR:
        return [Finding(Level.ESCALATE, "NT-9", f"confidence {conf} < {CONFIDENCE_FLOOR} on class-C — escalate", "solution.confidence", _pid(pair))]
    return [Finding(Level.PASS, "NT-9", f"confidence {conf}", "solution.confidence", _pid(pair))]


# ── Closed vocabularies (NT-6 / NT-14) ──────────────────────────────
# NT-6 and NT-14 are the legal-domain checks of the contract. The closed sets
# below are neutral defaults. Hosts can inject a versioned NormContractProfile
# without importing their domain modules into Solver.
INCIDENTS = ("claim-duty", "privilege", "power", "immunity", "disability")

_CONFLICT_PRINCIPLES = {
    "DE": ("lex-superior", "lex-specialis", "lex-posterior"),
    "EU": ("primacy", "lex-specialis", "lex-posterior"),
    "UK": ("parliamentary-sovereignty", "stare-decisis", "implied-repeal",
           "generalia-specialibus-non-derogant"),
    "US": ("constitutional-supremacy", "stare-decisis", "implied-repeal",
           "lex-specialis"),
}
_DEFAULT_LEGAL_SYSTEM = "DE"


def _conflict_principles(code=None):
    """Faithful to legal_systems.get(code).conflict_principles: default DE;
    an unknown code raises KeyError (a typo never silently picks a system)."""
    code = (code or _DEFAULT_LEGAL_SYSTEM).upper()
    if code not in _CONFLICT_PRINCIPLES:
        raise KeyError(f"unknown legal system {code!r}; available: "
                       f"{sorted(_CONFLICT_PRINCIPLES)}")
    return _CONFLICT_PRINCIPLES[code]


def check_collision(pair: dict, *, legal_system: str = "DE", principles=None) -> list[Finding]:
    """NT-6 Normkollision: stated meta-relations must be provenance-bound and
    must NOT carry a derived winner. A pair declaring a genuine conflict must
    set resolution='genuine-conflict-escalate' (which ESCALATES). The contract
    forbids an auto-resolution verdict on a conflict edge.

    The active legal system supplies which conflict principles the family even
    recognises (DE civil law: lex superior/specialis/posterior; common law:
    stare decisis / implied repeal) — recorded for the human, never auto-applied."""
    principles = ", ".join(
        _conflict_principles(legal_system) if principles is None else principles
    ) or "—"
    out: list[Finding] = []
    sol = _solution(pair)
    resolution = sol.get("resolution")
    # An explicit conflict must escalate, never silently resolve.
    if sol.get("predicate") == "may-conflict-with" or resolution == "genuine-conflict-escalate":
        if resolution and resolution not in {"genuine-conflict-escalate", "unresolved"}:
            out.append(Finding(Level.VIOLATION, "NT-6", f"conflict carries derived resolution {resolution!r} — collisions must escalate", "solution.resolution", _pid(pair)))
        else:
            out.append(Finding(Level.ESCALATE, "NT-6", f"genuine norm collision — human resolution required under {legal_system} principles ({principles})", "solution.resolution", _pid(pair)))
    # Stated meta-relations are fine, but only as provenance-bound edges.
    for e in _edges(pair):
        if e.get("predicate") in _META_RELATIONS and not (e.get("source") or e.get("cited")):
            out.append(Finding(Level.VIOLATION, "NT-6", f"meta-relation {e.get('predicate')!r} not provenance-bound", "edges[].source", _pid(pair)))
    if not out:
        out.append(Finding(Level.PASS, "NT-6", "no unresolved/auto-resolved collision", "solution.resolution", _pid(pair)))
    return out


def check_typed_dates(pair: dict) -> list[Finding]:
    """NT-11 typed-date-at-write: any date-bearing field a downstream runtime
    would *act on* (deadline, effective_date, due_date, until, expiry, and the
    events map) must be a valid ISO 8601 calendar date. A malformed value is a
    VIOLATION — the write should have been rejected, not deferred to a
    defensive parse at read time."""
    from .temporal import Date, TemporalError
    _DATE_KEYS = ("deadline", "effective_date", "due_date", "until", "expiry")
    out: list[Finding] = []
    checked = 0
    for scope_name, scope in (("solution", _solution(pair)), ("problem.facets", _facets(pair))):
        for key in _DATE_KEYS:
            val = scope.get(key)
            if val in (None, ""):
                continue
            checked += 1
            try:
                Date(str(val))
            except TemporalError:
                out.append(Finding(Level.VIOLATION, "NT-11",
                                   f"{key} is not a typed ISO date: {val!r}",
                                   f"{scope_name}.{key}", _pid(pair)))
        events = scope.get("events")
        if isinstance(events, dict):
            for k, v in events.items():
                checked += 1
                try:
                    Date(str(v))
                except TemporalError:
                    out.append(Finding(Level.VIOLATION, "NT-11",
                                       f"event {k!r} is not a typed ISO date: {v!r}",
                                       f"{scope_name}.events.{k}", _pid(pair)))
    if not out:
        msg = f"{checked} date field(s) typed" if checked else "no actionable date fields"
        out.append(Finding(Level.PASS, "NT-11", msg, "", _pid(pair)))
    return out


def check_predicate_floor(pair: dict) -> list[Finding]:
    """NT-12 predicate floor: a structured condition (``condition_struct``)
    must carry confidence >= the floor and validate as a Predicate. A
    sub-floor or malformed struct is a VIOLATION — the extractor should have
    abstained (left it None); the verbatim condition text is the honest
    fallback, a shaky struct is not."""
    sol = _solution(pair)
    structs: list[tuple[str, dict]] = []
    rule = sol.get("rule")
    if isinstance(rule, dict) and isinstance(rule.get("condition_struct"), dict):
        structs.append(("solution.rule.condition_struct", rule["condition_struct"]))
    if isinstance(sol.get("condition_struct"), dict):
        structs.append(("solution.condition_struct", sol["condition_struct"]))
    if not structs:
        return [Finding(Level.PASS, "NT-12", "no condition struct (verbatim only)", "", _pid(pair))]
    from .predicate import PREDICATE_CONFIDENCE_FLOOR, Predicate, PredicateError
    out: list[Finding] = []
    for path, struct in structs:
        try:
            p = Predicate.from_dict(struct)
        except (PredicateError, KeyError) as exc:
            out.append(Finding(Level.VIOLATION, "NT-12",
                               f"malformed condition_struct: {exc}", path, _pid(pair)))
            continue
        if p.confidence < PREDICATE_CONFIDENCE_FLOOR:
            out.append(Finding(Level.VIOLATION, "NT-12",
                               f"condition_struct confidence {p.confidence} < "
                               f"{PREDICATE_CONFIDENCE_FLOOR} — should have abstained",
                               path, _pid(pair)))
    if not out:
        out.append(Finding(Level.PASS, "NT-12",
                           f"{len(structs)} condition struct(s) at/above floor", "", _pid(pair)))
    return out


def check_incident_vocabulary(pair: dict, *, incidents=None) -> list[Finding]:
    """NT-14 juridical-primitive vocabulary: when the rule DNA carries an
    incident or condition_kind, the value must come from the closed
    vocabulary (Hohfeld layer, hohfeld.INCIDENTS) — '' is honest abstention
    and always conforming; an invented value is a VIOLATION."""
    rule = _solution(pair).get("rule")
    if not isinstance(rule, dict):
        return [Finding(Level.PASS, "NT-14", "no rule DNA on pair", "", _pid(pair))]
    out: list[Finding] = []
    inc = rule.get("incident", "")
    vocabulary = INCIDENTS if incidents is None else tuple(incidents)
    if inc not in ("", *vocabulary):
        out.append(Finding(Level.VIOLATION, "NT-14",
                           f"unknown incident {inc!r} (closed vocabulary)",
                           "solution.rule.incident", _pid(pair)))
    ck = rule.get("condition_kind", "")
    if ck not in ("", "suspensive", "resolutive"):
        out.append(Finding(Level.VIOLATION, "NT-14",
                           f"unknown condition_kind {ck!r}",
                           "solution.rule.condition_kind", _pid(pair)))
    if not out:
        out.append(Finding(Level.PASS, "NT-14", "primitive vocabulary conforming",
                           "", _pid(pair)))
    return out


# The contract = the ordered list of per-pair invariants (jurisdiction-agnostic
# ones). check_collision is jurisdiction-aware and is run separately.
_INVARIANTS = (
    check_provenance, check_temporal, check_applicability, check_deontic,
    check_exception, check_authority, check_jurisdiction,
    check_typed_dates, check_predicate_floor, check_incident_vocabulary,
)


def check_pair(pair: dict, *, risk_class: str = "B", legal_system: str = "DE",
               profile=None) -> ContractReport:
    """Run the full contract over one pair, under the selected legal system."""
    rep = ContractReport()
    for inv in _INVARIANTS:
        if inv is check_incident_vocabulary and profile is not None:
            rep.findings.extend(inv(pair, incidents=profile.incidents))
        else:
            rep.findings.extend(inv(pair))
    selected_system = profile.legal_system if profile is not None else legal_system
    principles = profile.conflict_principles if profile is not None else None
    rep.findings.extend(check_collision(pair, legal_system=selected_system,
                                        principles=principles))
    rep.findings.extend(check_confidence(pair, risk_class=risk_class))
    return rep


def enforce(pairs: Iterable[dict], *, risk_class: str = "B",
            legal_system: str = "DE", profile=None) -> ContractReport:
    """Run the contract over an ND's emitted pairs. The aggregate report's
    ``ok`` is False if ANY pair has a VIOLATION; ``must_escalate`` is True if
    any pair raises an ESCALATE."""
    rep = ContractReport()
    for p in pairs:
        rep.findings.extend(check_pair(p, risk_class=risk_class,
                                       legal_system=legal_system,
                                       profile=profile).findings)
    return rep


class ContractViolation(Exception):
    """Raised by :func:`gate` when an emission is non-conforming."""

    def __init__(self, report: ContractReport):
        self.report = report
        msg = "; ".join(f"{f.code} {f.message} [{f.pair_id}]" for f in report.violations)
        super().__init__(f"norm-theory contract violated: {msg}")


def gate(pairs: Iterable[dict], *, risk_class: str = "B",
         legal_system: str = "DE", profile=None) -> ContractReport:
    """Enforcement entry point. Returns the report on success (possibly with
    escalations to route); raises :class:`ContractViolation` on any VIOLATION.
    Wire into ``NDRouter.dispatch`` (post-extract) or a CI step."""
    pairs = list(pairs)
    rep = enforce(pairs, risk_class=risk_class, legal_system=legal_system,
                  profile=profile)
    if not rep.ok:
        raise ContractViolation(rep)
    return rep
