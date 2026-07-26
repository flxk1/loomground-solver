# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The reasoning contract — the universal pattern of a justified answer.

IRAC, Gutachtenstil and Fact–Rule–Meaning–Action are *presentation orderings*;
the structure they all order is one defeasible inference loop (Toulmin's layout
of argument, made defeasible):

    QUESTION → FACTS (evidenced) → NORMS (warranted) → APPLICATION (defeasible)
             → RESOLUTION (determinate XOR residual choice XOR open)
             → ACTION (deontic consequence — which produces new facts)

This module is the **substrate contract** over that pattern: enforceable
invariants a :class:`workspaces.problem_kg.CaseRecord` must satisfy before it may
stand. The formats become **profiles** — pure data, render vocabularies —
selectable per legal system or audience without touching logic.

Verdicts follow :mod:`workspaces.norm_contract` (PASS / VIOLATION / ESCALATE):
a malformed record is rejected; a well-formed record whose call belongs to a
human escalates. The invariants:

    R1  evidence     — every fact carries a source; every ground a receipt or
                       an explicit gap. Nothing unevidenced enters silently.
    R2  warrant      — every application step names what licenses the move
                       (the Toulmin warrant / the "Meaning" in FRMA), or is
                       explicitly flagged unwarranted → ESCALATE, never hidden.
    R3  resolution   — determinate XOR residual XOR open; a residual choice
                       names a real option and a non-empty rationale
                       (anti-rubber-stamp, mirrors decision_surface).
    R4  judgment floor —
                       Esc(q) ∧ Stake(q) ⟹ oversight level ≥ APPROVE;
                       (Esc(q) ∧ Stake(q)) ∨ Personal(q) ⟹ the resolution must
                       be *originated* by a human (a recorded choice with an
                       actor), never auto-emitted; Personal(q) additionally
                       requires level = MANUAL.
    R5  action       — actions derive only from a determinate answer or a
                       recorded choice, each citing its source norm. No action
                       from an open case.
    R6  custody (Workspace Lock alignment) — before a case record leaves the workspace
                       (export / print), its text is classified; findings
                       require either scrubbing or an explicitly acknowledged
                       export. Pure here: the classifier is injected.

Pure stdlib, operates on ``CaseRecord.to_dict()`` dicts. Policy/lock coupling
is via thin, lazily-imported helpers so the contract itself stays testable.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from .norm_contract import ContractReport, Finding, Level


# ── oversight levels (the §4a ladder; matches policy.py vocabulary) ──────────

LEVELS = ("autonomous", "notify", "review", "approve", "supervised", "manual")


def level_rank(level: str) -> int:
    lv = (level or "").strip().lower()
    if lv not in LEVELS:
        raise ValueError(f"unknown oversight level: {level!r} (known: {LEVELS})")
    return LEVELS.index(lv)


def required_oversight(*, esc: bool, stake: bool, personal: bool) -> str:
    """The judgment floor as a function."""
    if personal:
        return "manual"
    if esc and stake:
        return "approve"
    return "autonomous"


# ── information forms: WHAT the user is shown, per level ─────────────────────
# Information forms define role at the boundary, record verbosity, and what
# makes approval meaningful: informed, at least two options, visible
# consequences, and origination with own reasons.

INFORMATION_FORMS: dict[str, dict[str, str]] = {
    "autonomous": {
        "form": "record",
        "show": "nothing at run time; audit metadata in the mutation log",
        "interaction": "none — visibility only via the audit trail",
    },
    "notify": {
        "form": "notice",
        "show": "the question, the resolution state, and where the record is",
        "interaction": "informs; no gate",
    },
    "review": {
        "form": "preview",
        "show": "grounds with receipts, gaps, and the abstract schema — inspectable",
        "interaction": "inspectable; no gate",
    },
    "approve": {
        "form": "decision-surface",
        "show": "the readings with grounds AND consequences, none preferred; "
                "full case record one click away",
        "interaction": "gated on the output: human ratifies the single reading "
                       "or chooses among several, with a rationale",
    },
    "supervised": {
        "form": "transcript",
        "show": "the full phase transcript (every prompt, reply, repair) as it runs",
        "interaction": "gated on the process: human in the loop per phase",
    },
    "manual": {
        "form": "schema-only",
        "show": "the abstract reasoning schema, the sourced facts and the "
                "receipted grounds — and nothing drafted",
        "interaction": "human originates the resolution; the machine provides "
                       "the frame, never a candidate answer",
    },
}


def oversight_form(level: str) -> dict[str, str]:
    """The information form owed to the user at this oversight level."""
    return dict(INFORMATION_FORMS[LEVELS[level_rank(level)]])


# ── profiles — presentation orderings as data, never logic ───────────────────

PROFILES: dict[str, dict[str, Any]] = {
    "legal-de": {                        # Gutachtenstil
        "steps": ("norm", "tatbestand", "ausnahme", "subsumtion", "ergebnis"),
        "label": "Gutachtenstil (Obersatz–Definition–Subsumtion–Ergebnis)",
    },
    "legal-irac": {
        "steps": ("issue", "rule", "application", "conclusion"),
        "label": "IRAC",
    },
    "frma": {
        "steps": ("fact", "rule", "meaning", "action"),
        "label": "Fact–Rule–Meaning–Action",
    },
    "generic": {
        "steps": ("rule", "criteria", "defeater", "application", "conclusion"),
        "label": "Defeasible Toulmin loop (domain-neutral)",
    },
}
DEFAULT_PROFILE = "legal-de"


# ── accessors (tolerant; absence is what we check for) ───────────────────────

def _res(case: dict) -> dict:
    return case.get("resolution") or {}


def _cid(case: dict) -> str:
    return str((case.get("problem") or {}).get("text", ""))[:60]


def _is_esc(case: dict) -> bool:
    """Esc(q): the system left the status open — a residual or open case."""
    return _res(case).get("type") in ("residual", "open")


# ── the invariants ────────────────────────────────────────────────────────────

def check_evidence(case: dict) -> list[Finding]:
    """R1 — facts sourced; grounds receipted or in gaps; coverage consistent."""
    out: list[Finding] = []
    cid = _cid(case)
    for i, f in enumerate(case.get("facts") or []):
        if not (f.get("source") or "").strip():
            out.append(Finding(Level.VIOLATION, "RC-1",
                               f"fact #{i} carries no source — unevidenced "
                               f"premises may not enter silently",
                               field=f"facts[{i}]", pair_id=cid))
    for i, g in enumerate(case.get("grounds") or []):
        if not g.get("receipted"):
            out.append(Finding(Level.VIOLATION, "RC-1",
                               f"ground {g.get('pinpoint', i)} is neither "
                               f"receipted nor reported as a gap",
                               field=f"grounds[{i}]", pair_id=cid))
    gaps, cov = case.get("gaps") or [], case.get("coverage", 1.0)
    if gaps and cov >= 1.0:
        out.append(Finding(Level.VIOLATION, "RC-1",
                           "gaps present but coverage claims 1.0 — a hidden gap",
                           field="coverage", pair_id=cid))
    for i, w in enumerate(case.get("waivers") or []):
        if not (w.get("actor") or "").strip() or not (w.get("rationale") or "").strip():
            out.append(Finding(Level.VIOLATION, "RC-1",
                               f"waiver of {w.get('gap', '?')} without actor or "
                               f"rationale — a gap is owned, never waved away",
                               field=f"waivers[{i}]", pair_id=cid))
    if not out:
        out.append(Finding(Level.PASS, "RC-1", "evidence sound", pair_id=cid))
    return out


def check_warrants(case: dict) -> list[Finding]:
    """R2 — each application step warranted, or flagged and escalated."""
    out: list[Finding] = []
    cid = _cid(case)
    for i, step in enumerate(case.get("chain") or []):
        if (step.get("warrant") or "").strip():
            continue
        if step.get("unwarranted") is True:
            out.append(Finding(Level.ESCALATE, "RC-2",
                               f"step '{step.get('step', i)}' explicitly "
                               f"unwarranted — flagged for a human",
                               field=f"chain[{i}]", pair_id=cid))
        else:
            out.append(Finding(Level.ESCALATE, "RC-2",
                               f"step '{step.get('step', i)}' names no warrant "
                               f"(what licenses this move?)",
                               field=f"chain[{i}]", pair_id=cid))
    if not out:
        out.append(Finding(Level.PASS, "RC-2", "all steps warranted", pair_id=cid))
    return out


def check_resolution(case: dict) -> list[Finding]:
    """R3 — determinate XOR residual XOR open; choices are real and reasoned."""
    out: list[Finding] = []
    cid = _cid(case)
    r = _res(case)
    rtype = r.get("type")
    if rtype not in ("determinate", "residual", "open"):
        out.append(Finding(Level.VIOLATION, "RC-3",
                           f"unknown resolution type {rtype!r}",
                           field="resolution.type", pair_id=cid))
    if rtype == "determinate" and not (r.get("answer") or "").strip():
        out.append(Finding(Level.VIOLATION, "RC-3", "determinate without an answer",
                           field="resolution.answer", pair_id=cid))
    if rtype == "residual":
        opts = (r.get("surface") or {}).get("options") or []
        if len(opts) < 2:
            out.append(Finding(Level.VIOLATION, "RC-3",
                               "residual with fewer than 2 options — that is a "
                               "disguised answer, not a choice",
                               field="resolution.surface", pair_id=cid))
        ch = r.get("choice")
        if ch is not None:
            ids = {o.get("id") for o in opts}
            if ch.get("chosen_option_id") not in ids:
                out.append(Finding(Level.VIOLATION, "RC-3",
                                   "chosen option is not one of the presented options",
                                   field="resolution.choice", pair_id=cid))
            if not (ch.get("rationale") or "").strip():
                out.append(Finding(Level.VIOLATION, "RC-3",
                                   "choice without rationale — rubber stamp",
                                   field="resolution.choice.rationale", pair_id=cid))
        else:
            out.append(Finding(Level.ESCALATE, "RC-3",
                               "residual with no recorded choice — OPEN, awaiting a human",
                               field="resolution.choice", pair_id=cid))
    if not out:
        out.append(Finding(Level.PASS, "RC-3", "resolution well-formed", pair_id=cid))
    return out


def check_judgment_floor(case: dict, *, oversight_level: str = "autonomous",
                         oversight_active: bool = True,
                         stake: bool = False, personal: bool = False) -> list[Finding]:
    """R4 — Oversight alignment. Esc∧Stake ⟹ ℓ ≥ APPROVE; (Esc∧Stake)∨Personal
    ⟹ human origination; Personal ⟹ ℓ = MANUAL. Oversight disabled ⇒ effective
    level is AUTONOMOUS regardless of the configured default."""
    out: list[Finding] = []
    cid = _cid(case)
    eff = oversight_level if oversight_active else "autonomous"
    esc = _is_esc(case)
    floor = required_oversight(esc=esc, stake=stake, personal=personal)
    if level_rank(eff) < level_rank(floor):
        out.append(Finding(Level.VIOLATION, "RC-4",
                           f"judgment floor breached: Esc={esc}, Stake={stake}, "
                           f"Personal={personal} requires ≥ {floor.upper()}, "
                           f"effective level is {eff.upper()}"
                           + ("" if oversight_active else " (oversight disabled)"),
                           field="oversight", pair_id=cid))
    if (esc and stake) or personal:
        ch = _res(case).get("choice")
        if _res(case).get("type") == "determinate":
            out.append(Finding(Level.VIOLATION, "RC-4",
                               "auto-emitted determinate answer where origination "
                               "must lie with a human (§4a.9)",
                               field="resolution", pair_id=cid))
        elif ch is not None and not (ch.get("actor") or "").strip():
            out.append(Finding(Level.VIOLATION, "RC-4",
                               "recorded choice has no human actor — origination "
                               "unattributable",
                               field="resolution.choice.actor", pair_id=cid))
        elif ch is None:
            out.append(Finding(Level.ESCALATE, "RC-4",
                               "awaiting human origination (Esc∧Stake or Personal)",
                               field="resolution.choice", pair_id=cid))
    if not out:
        out.append(Finding(Level.PASS, "RC-4", "judgment floor satisfied", pair_id=cid))
    return out


def check_actions(case: dict, *, held_pinpoints: Optional[set] = None) -> list[Finding]:
    """R5 — actions only from a determinate answer or a recorded choice; each
    action cites its source norm. With ``held_pinpoints`` (what the corpus
    actually holds), a citation that does not RESOLVE escalates: a well-formed
    but corpus-unverifiable instruction is a human's to verify, never silently
    trusted."""
    out: list[Finding] = []
    cid = _cid(case)
    actions = case.get("actions") or []
    r = _res(case)
    resolved = (r.get("type") == "determinate"
                or (r.get("type") == "residual" and r.get("choice")))
    if actions and not resolved:
        out.append(Finding(Level.VIOLATION, "RC-5",
                           "actions attached to an unresolved case — nothing may "
                           "be done on an open question",
                           field="actions", pair_id=cid))
    for i, a in enumerate(actions):
        if not (a.get("obligation") or "").strip():
            out.append(Finding(Level.VIOLATION, "RC-5",
                               f"action #{i} states no obligation",
                               field=f"actions[{i}]", pair_id=cid))
        sn = (a.get("source_norm") or "").strip()
        if not sn:
            out.append(Finding(Level.VIOLATION, "RC-5",
                               f"action #{i} cites no source norm — an unanchored "
                               f"instruction",
                               field=f"actions[{i}]", pair_id=cid))
        elif held_pinpoints is not None and \
                not any(p and p in sn for p in held_pinpoints):
            out.append(Finding(Level.ESCALATE, "RC-5",
                               f"action #{i} cites {sn!r} — a provision the corpus "
                               f"does not hold; verify before relying on it",
                               field=f"actions[{i}]", pair_id=cid))
    if not out:
        out.append(Finding(Level.PASS, "RC-5", "actions anchored", pair_id=cid))
    return out


def check_norm_completeness(case: dict) -> list[Finding]:
    """RC-8 — read the norm to the end. A ground whose own text carries an
    exception ("unless …", Abs. 3, Ausnahme) is not applied until that
    exception is EXAMINED: a determinate answer or proposed reading over such
    a ground requires a chain step that addresses it (an Ausnahme/Defeater
    step, or a step whose text/warrant engages the exception wording).
    Otherwise the case escalates — half-read law never auto-closes."""
    out: list[Finding] = []
    cid = _cid(case)
    res = _res(case)
    closing = (res.get("type") == "determinate") or bool(res.get("proposed"))
    if closing:
        chain = case.get("chain") or []
        exception_steps = [s for s in chain
                           if (s.get("step") or "").strip().lower()
                           in ("ausnahme", "defeater", "exception", "rebuttal")
                           or "unless" in (s.get("text", "") + s.get("warrant", "")).lower()
                           or "ausnahme" in (s.get("text", "") + s.get("warrant", "")).lower()]
        for g in case.get("grounds") or []:
            exc = (g.get("exception") or "").strip()
            if not exc:
                continue
            sig = " ".join(exc.lower().split()[:6])
            addressed = any(sig[:40] in (s.get("text", "") + " " + s.get("warrant", "")).lower()
                            or s in exception_steps for s in chain)
            if not addressed:
                out.append(Finding(Level.ESCALATE, "RC-8",
                                   f"{g.get('pinpoint', '?')} carries an exception "
                                   f"('{exc[:70]}…') that no chain step examines — "
                                   f"the norm was not read to the end",
                                   field="chain", pair_id=cid))
    if not out:
        out.append(Finding(Level.PASS, "RC-8", "norms read to the end", pair_id=cid))
    return out


def check_profile(case: dict) -> list[Finding]:
    """Profiles are data: unknown profile or off-vocabulary steps ESCALATE
    (a labelling problem, not a malformed record)."""
    out: list[Finding] = []
    cid = _cid(case)
    prof = case.get("profile") or DEFAULT_PROFILE
    if prof not in PROFILES:
        out.append(Finding(Level.ESCALATE, "RC-7",
                           f"unknown profile {prof!r} — rendering vocabulary "
                           f"unresolved", field="profile", pair_id=cid))
        return out
    vocab = set(PROFILES[prof]["steps"])
    for i, step in enumerate(case.get("chain") or []):
        if (step.get("step") or "").strip().lower() not in vocab:
            out.append(Finding(Level.ESCALATE, "RC-7",
                               f"step '{step.get('step')}' not in {prof} vocabulary",
                               field=f"chain[{i}]", pair_id=cid))
    if not out:
        out.append(Finding(Level.PASS, "RC-7", f"profile {prof} consistent", pair_id=cid))
    return out


# ── aggregate check + gate ────────────────────────────────────────────────────

def check_case(case: dict, *, oversight_level: str = "autonomous",
               oversight_active: bool = True,
               stake: bool = False, personal: bool = False,
               held_pinpoints: Optional[set] = None) -> ContractReport:
    rep = ContractReport()
    rep.findings.extend(check_evidence(case))
    rep.findings.extend(check_warrants(case))
    rep.findings.extend(check_resolution(case))
    rep.findings.extend(check_judgment_floor(case, oversight_level=oversight_level,
                                             oversight_active=oversight_active,
                                             stake=stake, personal=personal))
    rep.findings.extend(check_actions(case, held_pinpoints=held_pinpoints))
    rep.findings.extend(check_norm_completeness(case))
    rep.findings.extend(check_profile(case))
    return rep


class ReasoningViolation(Exception):
    def __init__(self, report: ContractReport):
        self.report = report
        msg = "; ".join(f"{f.code} {f.message}" for f in report.violations)
        super().__init__(f"reasoning contract violated: {msg}")


def gate(case: dict, **kw) -> ContractReport:
    """Enforcement entry point (mirrors norm_contract.gate): returns the report,
    raises :class:`ReasoningViolation` on any VIOLATION. Escalations pass
    through for routing to the decision surface / oversight prompt."""
    rep = check_case(case, **kw)
    if not rep.ok:
        raise ReasoningViolation(rep)
    return rep


# ── Workspace Lock alignment: custody of the record at the boundary (R6) ──────────

def check_export(cases: Iterable[dict], *,
                 classify: Optional[Callable[[str], dict]] = None,
                 acknowledged: bool = False) -> ContractReport:
    """R6 — a case record leaving the workspace (print/export) is classified first.
    ``classify(text) -> {"findings": int, ...}`` is injected (lock_classify /
    Privacy Lock); positive findings ESCALATE unless the export is explicitly
    acknowledged. No classifier injected ⇒ ESCALATE (custody unknown beats
    custody assumed)."""
    rep = ContractReport()
    for case in cases:
        cid = _cid(case)
        texts = [case.get("problem", {}).get("text", "")]
        texts += [f.get("text", "") for f in case.get("facts") or []]
        ch = _res(case).get("choice") or {}
        texts.append(ch.get("rationale", ""))
        if classify is None:
            rep.findings.append(Finding(Level.ESCALATE, "RC-6",
                                        "export without lock classification — "
                                        "custody state unknown",
                                        field="export", pair_id=cid))
            continue
        n = sum(int(classify(t).get("findings", 0)) for t in texts if t)
        if n and not acknowledged:
            rep.findings.append(Finding(Level.ESCALATE, "RC-6",
                                        f"{n} lock finding(s) in the record — scrub, "
                                        f"seal (Workspace Lock), or acknowledge the export",
                                        field="export", pair_id=cid))
        else:
            rep.findings.append(Finding(Level.PASS, "RC-6",
                                        "custody clear" if not n else
                                        f"{n} finding(s), export acknowledged",
                                        pair_id=cid))
    return rep
