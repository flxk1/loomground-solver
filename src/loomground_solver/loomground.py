# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Loomground — a standalone conforming implementation of the language.

The parser, well-formedness validator, token validator, transport evaluator,
and observation projection follow the published Loomground specification and
are gated by its conformance vectors. No host, graph, or governance runtime is
imported.

Vocabulary: nodes actor|human|gate|master; cords authority(actor->gate)
| pipe(gate->gate) | egress(gate->master); verdicts auto|human|refused|reserved
|prohibited (strictest-wins join); declarations reserve|prohibit|obligation|
redress|delegation|mandate|transfer (the acyclic principal chain, v0.9+; role
canonicalization and the ISO/IEC 22989 autonomy ladder, v0.10; host-observed
`kind` and gate-computed `risk`, PROM-001, v0.11 — see prom001.py).
"""
from __future__ import annotations

import re
from typing import Any, Optional

from loomground_governance import (
    canonical_roles, canonicalize_role, language_version, vocabulary,
)


# ── authoritative language artifacts ────────────────────────────────────────
# Grammar, vocabulary, schemas, versions and conformance vectors come from the
# data-only loomground-governance package published by the language repository.
# This module implements them; it never redefines their values.
LANGUAGE_VERSION = language_version()
SUPPORTED_LANGUAGE_VERSIONS = tuple(dict.fromkeys((
    "0.7", "0.8.2", "0.9", "0.10", "0.11", LANGUAGE_VERSION,
)))
RISKS = list(vocabulary("risk")["levels"])
RISK_RANK = {r: i for i, r in enumerate(RISKS)}

# v0.9.0 declared, ordered token properties (SPEC §4): `reversibility` states
# how recoverable a released effect is; `uncertainty` states how settled the
# basis for the action is. Both are asserted by whoever supplies the token —
# never derived — and both order ascending in concern, exactly as `risk`.
REVERSIBILITY = list(vocabulary("reversibility")["levels"])
REVERSIBILITY_RANK = {r: i for i, r in enumerate(REVERSIBILITY)}
UNCERTAINTY = list(vocabulary("uncertainty")["levels"])
UNCERTAINTY_RANK = {u: i for i, u in enumerate(UNCERTAINTY)}
# every ordered, guardable token property with a >=/= domain (kind and party
# are matched by equality only and carry no order — see GUARD_OPS below).
_ORDERED_RANKS = {"risk": RISK_RANK, "reversibility": REVERSIBILITY_RANK,
                   "uncertainty": UNCERTAINTY_RANK}

# §6 guard domain — sourced from vocabulary/guard-domain.json, never
# re-declared: `ranges_over` is the guard-field domain (amended v0.5 tags-guard,
# v0.9.0 reversibility/uncertainty) and `operators` is each field's fixed
# operator set. NEVER `id` or `provenance` (the no-id wall), never `grade`
# (configuration, not a token field). `tags contains <tag>` is membership over a
# declared, non-id category set; it denotes no computed value. Enforced at
# APPLY stage (validate), not in the grammar.
_GUARD_DOMAIN = vocabulary("guard-domain")
GUARD_FIELDS = set(_GUARD_DOMAIN["ranges_over"])
GUARD_OPS = {field: set(ops) for field, ops in _GUARD_DOMAIN["operators"].items()}

# §6 role canonicalization (v0.10.0, POLICY: vocabulary/roles.json): maps a raw
# bearer span (e.g. "the data protection officer") to a canonical governance
# role id and node kind (agent/human). The language's `role = id` grammar
# accepts only the canonical id, never the raw span — a host or ingest layer
# resolves free text to that id BEFORE emitting a `human ... role <id>`
# declaration or a reservation `by <role>` target. Consumed here, never
# re-declared: the solver hardcodes no role or alias of its own. Both names are
# imported above and re-exported unchanged from this module's namespace.

# §6/§7.1 autonomy GRADE (amended v0.6; v0.10.0 aligns the default ladder to the
# ISO/IEC 22989 §5.13 autonomy axis, L0..L6): a `grade` GRANTED on an actor and
# REQUIRED on a SOURCE gate gates the step-(4) auto/human disposition — auto iff
# G ≥ R, an ungraded actor at a graded gate is human (fail-closed), a gate with
# no required grade is policy (grade inert). The ladder + level meanings are
# POLICY (loomground vocabulary/grades.json); read from there, not re-declared.
# grade is a CONFIG attribute, not a token field, NOT guardable. Additive — a
# gradeless graph is unchanged.
GRADES = list(vocabulary("grades")["levels"])
GRADE_RANK = {g: i for i, g in enumerate(GRADES)}
_GRADE_MAX_RANK = len(GRADES) - 1


def grade_rank(grade: Any) -> int:
    """Rank a grade on the ordered ladder. Accepts the language form ("L0".."L6")
    or an adapter's integer rank (0..len(GRADES)-1). Anything not recognised —
    None, an out-of-range int, a bool, a bad string — ranks below L0 (-1), i.e.
    treated as ungraded. That is the fail-safe reading on the GRANTED side (an
    unrecognised grant earns nothing); `grade_meets` separately refuses an
    unrecognised REQUIREMENT, so a malformed value can never silently grant auto."""
    if grade is None or isinstance(grade, bool):
        return -1
    if isinstance(grade, int):
        return grade if 0 <= grade <= _GRADE_MAX_RANK else -1  # out-of-range int = unrecognised
    return GRADE_RANK.get(grade, -1)


def grade_meets(granted: Any, required: Any) -> bool:
    """Canonical autonomy-grade COMPARISON (v0.6 §7.1 step-(4)): does a GRANTED grade
    meet a REQUIRED one? This is the SINGLE authority both the language `evaluate()`
    and host adapters may consult. The language compares a gate's own required
    grade against the proposing actor's granted grade; adapters can reuse the
    same comparison without duplicating the rule.

    Fail-closed on every malformed input: a required grade of None means "no
    requirement" → always met (grade inert; policy as before); a required grade that is
    present but unrecognised (out-of-range int, bad string) can NEVER be satisfied →
    human; an ungraded/unrecognised GRANTED grade never meets a real requirement. Accepts
    "Lk" or int on either side, so language strings and app integer ranks compare without
    coupling the two layers."""
    if required is None:
        return True
    rr = grade_rank(required)
    if rr < 0:                       # requirement present but unrecognised → un-meetable
        return False
    return grade_rank(granted) >= rr
# verdict restrictiveness order — from loomground vocabulary/verdicts.json (one source)
VERDICTS = list(vocabulary("verdicts")["restrictiveness_order"])
VERDICT_RANK = {v: i for i, v in enumerate(VERDICTS)}
MASTER = "master"

# The engine's assumed node classes and cord types. Loomground defines these in
# vocabulary/node-classes.json and vocabulary/cords.json; the engine hardcodes them
# (in parse/validate/project), so they are declared here as the single in-engine
# anchor and test_loomground_parity.py asserts they equal the live Loomground data.
NODE_CLASSES = {"actor", "human", "gate", "master"}
CORD_TYPES = {"authority", "pipe", "egress"}
_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


class ParseError(ValueError):
    """Raised at parse stage (grammar error): missing arrow, unknown keyword."""


class ApplyError(ValueError):
    """Raised when a parsed policy graph is not well formed."""

    def __init__(self, errors):
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


# ── §7 rack: pure textual macro pre-pass ──────────────────────────────────────
def expand_racks(text: str) -> str:
    """Expand `rack`/`rack-use` macros before the grammar is applied (SYNTAX §7).

    Fail-closed: unknown rack name, arity mismatch, undefined $name, or a missing
    `end` denotes an ill-formed program -> ParseError.
    """
    lines = text.splitlines()
    defs: dict[str, tuple[list[str], list[str]]] = {}
    out: list[str] = []
    i = 0
    use_counter = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        m = re.match(r"^rack\s+([A-Za-z][\w-]*)\s*\(([^)]*)\)\s*:\s*$", s)
        if m:
            name = m.group(1)
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            body: list[str] = []
            i += 1
            closed = False
            while i < len(lines):
                bs = lines[i].strip()
                if bs == "end":
                    closed = True
                    break
                body.append(lines[i])
                i += 1
            if not closed:
                raise ParseError("rack: missing 'end'")
            defs[name] = (params, body)
            i += 1
            continue
        m = re.match(r"^rack-use\s+([A-Za-z][\w-]*)\s*\(([^)]*)\)\s*$", s)
        if m:
            name = m.group(1)
            if name not in defs:
                raise ParseError(f"rack-use: unknown rack {name!r}")
            params, body = defs[name]
            bindings: dict[str, str] = {}
            for b in (x.strip() for x in m.group(2).split(",") if x.strip()):
                if "=" not in b:
                    raise ParseError(f"rack-use: bad binding {b!r}")
                k, v = b.split("=", 1)
                bindings[k.strip()] = v.strip()
            if set(bindings) != set(params):
                raise ParseError(
                    f"rack-use {name}: args {sorted(bindings)} != params {sorted(params)}"
                )
            idx = str(use_counter)
            use_counter += 1
            for bl in body:
                expanded = bl.replace("$0", idx)
                for p in params:
                    expanded = expanded.replace(f"${p}", bindings[p])
                if "$" in re.sub(r"\$0", "", expanded):
                    # any surviving $name is undefined
                    if re.search(r"\$[A-Za-z]", expanded):
                        raise ParseError(f"rack-use {name}: undefined placeholder in {bl!r}")
                out.append(expanded)
            i += 1
            continue
        out.append(raw)
        i += 1
    return "\n".join(out)


# ── §2/§3 parser: text -> patch (abstract policy graph as data) ────────────────
def parse(text: str) -> dict[str, Any]:
    """Parse the .lg textual surface into a patch dict. Raises ParseError on a
    grammar error (parse stage). Semantic legality is checked in validate()."""
    text = expand_racks(text)
    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    grants: list[dict[str, Any]] = []
    cords: list[dict[str, Any]] = []
    reservations: list[dict[str, Any]] = []
    prohibitions: list[dict[str, Any]] = []
    obligations: list[dict[str, Any]] = []
    redress: list[dict[str, Any]] = []
    transfers: list[dict[str, Any]] = []

    def add_node(rec: dict[str, Any]) -> None:
        nodes.append(rec)
        node_ids.add(rec["id"])

    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        tok = line.split()
        kw = tok[0]

        if kw == "actor":
            if len(tok) < 2:
                raise ParseError(f"line {n}: actor needs an id")
            rec: dict[str, Any] = {"id": tok[1], "class": "actor"}
            i = 2
            while i < len(tok):
                if tok[i] == "party" and i + 1 < len(tok):
                    rec["party"] = tok[i + 1]; i += 2
                elif tok[i] == "on-behalf-of" and i + 1 < len(tok):
                    # a second delegator on one actor is grammatical but ill-formed
                    # at apply (§6: at most one); keep every binding for validate()
                    if "on_behalf_of" in rec:
                        rec.setdefault("on_behalf_of_extra", []).append(tok[i + 1])
                    else:
                        rec["on_behalf_of"] = tok[i + 1]
                    i += 2
                elif tok[i] == "grade" and i + 1 < len(tok):
                    rec["grade"] = tok[i + 1]; i += 2          # v0.6: granted autonomy grade
                elif tok[i] == "mandate" and i + 1 < len(tok):
                    # v0.9.0: the set of declared purposes this actor is authorised
                    # to pursue. A second `mandate` on the same actor is grammatical
                    # but ill-formed at apply (§6: at most one) — mirrors on-behalf-of.
                    purposes, consumed = _parse_purpose_set(tok, i + 1, n)
                    if "mandate" in rec:
                        rec.setdefault("mandate_extra", []).append(purposes)
                    else:
                        rec["mandate"] = purposes
                    i += 1 + consumed
                elif tok[i] == "name":
                    rec["name"] = " ".join(tok[i + 1:]); i = len(tok)
                else:
                    raise ParseError(f"line {n}: bad actor option {tok[i]!r}")
            add_node(rec)

        elif kw == "human":
            if len(tok) < 2:
                raise ParseError(f"line {n}: human needs an id")
            rec = {"id": tok[1], "class": "human"}
            i = 2
            while i < len(tok):
                if tok[i] == "role" and i + 1 < len(tok):
                    rec["role"] = tok[i + 1]; i += 2
                elif tok[i] == "name":
                    rec["name"] = " ".join(tok[i + 1:]); i = len(tok)
                else:
                    raise ParseError(f"line {n}: bad human option {tok[i]!r}")
            add_node(rec)

        elif kw == "gate":
            if len(tok) < 2:
                raise ParseError(f"line {n}: gate needs an id")
            rec = {"id": tok[1], "class": "gate"}
            i = 2
            while i < len(tok):
                if tok[i] == "risk" and i + 1 < len(tok):
                    rec["risk_floor"] = tok[i + 1]; i += 2
                elif tok[i] == "party" and i + 1 < len(tok):
                    rec["party"] = tok[i + 1]; i += 2
                elif tok[i] == "grade" and i + 1 < len(tok):
                    rec["grade_required"] = tok[i + 1]; i += 2  # v0.6: required grade (source gate)
                elif tok[i] == "consign" and i + 1 < len(tok):
                    rec["consignee"] = tok[i + 1]; i += 2       # v0.9.0: the party this gate's release goes to
                elif tok[i] == "name" and i + 1 < len(tok):
                    rec["name"] = tok[i + 1]; i += 2
                elif tok[i] == "grant":
                    # grant clause MUST be last; consumes the rest of the line
                    for g in tok[i + 1:]:
                        grants.append(_parse_grant(rec["id"], g, n))
                    i = len(tok)
                else:
                    raise ParseError(f"line {n}: bad gate option {tok[i]!r}")
            add_node(rec)

        elif kw == "cord":
            # cord = "cord" endpoint "->" endpoint
            if "->" not in tok:
                raise ParseError(f"line {n}: cord without '->'")
            ar = tok.index("->")
            if ar != 2 or len(tok) != 4:
                raise ParseError(f"line {n}: cord must be 'cord A -> B'")
            cords.append({"from": tok[1], "to": tok[3]})

        elif kw == "reserve":
            reservations.append(_parse_reserve(tok, n))

        elif kw == "prohibit":
            prohibitions.append(_parse_prohibit(tok, n))

        elif kw == "obligation":
            # obligation <obligation> on <gate>
            if len(tok) != 4 or tok[2] != "on":
                raise ParseError(f"line {n}: obligation must be '<obligation> on <gate>'")
            obligations.append({"obligation": tok[1], "on": tok[3]})

        elif kw == "redress":
            redress.append(_parse_redress(tok, n))

        elif kw == "transfer":
            transfers.append(_parse_transfer(tok, n))

        else:
            raise ParseError(f"line {n}: unknown keyword {kw!r}")

    patch: dict[str, Any] = {"nodes": nodes, "cords": cords}
    if grants:
        patch["grants"] = grants
    patch["reservations"] = reservations
    if prohibitions:
        patch["prohibitions"] = prohibitions
    if obligations:
        patch["obligations"] = obligations
    if redress:
        patch["redress"] = redress
    if transfers:
        patch["transfers"] = transfers
    return patch


def _parse_purpose_set(tok: list[str], i: int, n: int) -> tuple[list[str], int]:
    """Parse a `purpose set` (SYNTAX §3) starting at tok[i]: a bare purpose id,
    or a brace-delimited set `{p, p, ...}`. Returns (purposes, tokens consumed).
    Mirrors the quorum-target join-then-regex approach in _parse_reserve — the
    braces MAY contain internal whitespace even though the surface has already
    been whitespace-tokenised."""
    if i >= len(tok):
        raise ParseError(f"line {n}: expected a purpose set")
    if tok[i].startswith("{"):
        rest = " ".join(tok[i:])
        m = re.match(r"^\{([^}]*)\}", rest)
        if not m:
            raise ParseError(f"line {n}: bad purpose set {rest!r}")
        purposes = [p.strip() for p in m.group(1).split(",") if p.strip()]
        return purposes, len(m.group(0).split())
    return [tok[i]], 1


def _parse_transfer(tok: list[str], n: int) -> dict[str, Any]:
    # transfer <kind> to <consignee> within <purpose-set>
    if len(tok) < 6 or tok[2] != "to" or tok[4] != "within":
        raise ParseError(f"line {n}: transfer must be '<kind> to <consignee> within <purposes>'")
    purposes, _consumed = _parse_purpose_set(tok, 5, n)
    return {"kind": tok[1], "to": tok[3], "within": purposes}


def _parse_grant(gate: str, g: str, n: int) -> dict[str, Any]:
    m = re.match(r"^([A-Za-z][\w-]*)(?:\[([^\]]*)\])?$", g)
    if not m:
        raise ParseError(f"line {n}: bad grant {g!r}")
    actor = m.group(1)
    rec: dict[str, Any] = {"gate": gate, "actor": actor}
    body = m.group(2)
    if body:
        if ":" in body:
            kinds_part, risks_part = body.split(":", 1)
            rec["kinds"] = [k.strip() for k in kinds_part.split(",") if k.strip()]
            rec["risks"] = [r.strip() for r in risks_part.split(",") if r.strip()]
        else:
            rec["kinds"] = [k.strip() for k in body.split(",") if k.strip()]
    return rec


def _parse_guard(tok: list[str], i: int) -> tuple[Optional[str], int]:
    """Parse a 'when <guard>' tail starting at tok[i]=='when'. Returns (guard_str, next_i)."""
    if i >= len(tok) or tok[i] != "when":
        return None, i
    # guard = kind = X | risk relop value | party = Y  (3 tokens)
    if len(tok) - i < 3:
        raise ParseError("guard: incomplete")
    g = tok[i + 1: i + 4]
    if len(g) < 3:
        raise ParseError("guard: incomplete")
    return " ".join(g), i + 4


def _parse_reserve(tok: list[str], n: int) -> dict[str, Any]:
    # reserve <kind> by <target> [when <guard>] [duration <d> : <on-elapse>]
    if len(tok) < 4 or tok[2] != "by":
        raise ParseError(f"line {n}: reserve must be '<kind> by <target> ...'")
    rec: dict[str, Any] = {"kind": tok[1]}
    i = 3
    # target: role | role and role | N of { r, ... }
    if i < len(tok) and tok[i].isdigit() and i + 1 < len(tok) and tok[i + 1] == "of":
        # quorum: N of { ... }
        j = i
        rest = " ".join(tok[i:])
        m = re.match(r"^(\d+)\s+of\s+\{([^}]*)\}", rest)
        if not m:
            raise ParseError(f"line {n}: bad quorum target")
        # SPEC §9 canonical form (conformance-pinned by the reserve-quorum vector):
        # exactly one space after `of` and after each
        # comma, none adjacent to the braces — so two spellings of one target compare
        # equal. (Token-joining already normalised runs of whitespace; commas are
        # normalised here. An empty role set survives as `{}` for validate() to flag.)
        roles = [x.strip() for x in m.group(2).split(",") if x.strip()]
        rec["by"] = f"{m.group(1)} of {{{', '.join(roles)}}}"
        consumed = len(m.group(0).split())
        i = i + consumed
    elif i + 2 < len(tok) and tok[i + 1] == "and":
        rec["by"] = f"{tok[i]} and {tok[i + 2]}"
        i += 3
    else:
        rec["by"] = tok[i]
        i += 1
    guard, i = _parse_guard(tok, i)
    if guard is not None:
        rec["when"] = guard
    if i < len(tok) and tok[i] == "duration":
        # duration <d> : <on-elapse>
        rest = tok[i + 1:]
        if len(rest) >= 3 and rest[1] == ":":
            rec["duration"] = rest[0]
            rec["on_elapse"] = rest[2]
        else:
            raise ParseError(f"line {n}: bad duration clause")
    return rec


def _parse_prohibit(tok: list[str], n: int) -> dict[str, Any]:
    # prohibit <kind> [when <guard>]
    if len(tok) < 2:
        raise ParseError(f"line {n}: prohibit needs a kind")
    rec: dict[str, Any] = {"kind": tok[1]}
    guard, _ = _parse_guard(tok, 2)
    if guard is not None:
        rec["when"] = guard
    return rec


def _parse_redress(tok: list[str], n: int) -> dict[str, Any]:
    # redress <kind> by <role> [overturn] [within <duration>]
    if len(tok) < 4 or tok[2] != "by":
        raise ParseError(f"line {n}: redress must be '<kind> by <role> ...'")
    rec: dict[str, Any] = {"kind": tok[1], "by": tok[3], "overturn": False, "within": None}
    i = 4
    while i < len(tok):
        if tok[i] == "overturn":
            rec["overturn"] = True; i += 1
        elif tok[i] == "within" and i + 1 < len(tok):
            rec["within"] = tok[i + 1]; i += 2
        else:
            raise ParseError(f"line {n}: bad redress option {tok[i]!r}")
    return rec


# ── §4 well-formedness (apply stage) ───────────────────────────────────────────
def validate(patch: dict[str, Any]) -> dict[str, Any]:
    """Return {ok, errors}. Apply-stage legality of the abstract policy graph."""
    errors: list[str] = []
    # node ids share one namespace (id grammar §3): a duplicate id is ill-formed
    _ids = [nd.get("id") for nd in patch.get("nodes", [])]
    _dupes = sorted({i for i in _ids if _ids.count(i) > 1})
    if _dupes:
        errors.append(f"duplicate node id(s): {_dupes}")
    by_id = {nd["id"]: nd for nd in patch.get("nodes", [])}
    actors = {i for i, nd in by_id.items() if nd["class"] == "actor"}
    humans = {i for i, nd in by_id.items() if nd["class"] == "human"}
    gates = {i for i, nd in by_id.items() if nd["class"] == "gate"}

    # risk floor must be in the risk domain
    for nd in patch.get("nodes", []):
        if nd["class"] == "gate" and "risk_floor" in nd:
            if nd["risk_floor"] not in RISK_RANK:
                errors.append(f"gate {nd['id']!r}: risk {nd['risk_floor']!r} not in {RISKS}")

    # §6 guard-field domain / no-id wall. The parser accepts any 3-token `when`
    # tail (grammar); legality is decided HERE (apply stage) — a guard over `id` or
    # `provenance` is forbidden, and each field has a fixed operator set. This
    # closes the accept-and-defer gap for `id` and `provenance` guards.
    # A tag-guard on a PROHIBITION is sanctioned by Loomground v0.6 (§6, the
    # `prohibit-tags` conformance vector): a guarded prohibition prohibits exactly the
    # matched subset (membership over a declared category, not branching on identity).
    # Tag-guards are not restricted to reservations; `evaluate` already applies
    # this correctly for both declaration kinds. v0.9.0 admits `reversibility` and
    # `uncertainty` on exactly the terms `risk` already has (>=, =) — the same
    # ordered-domain check below applies to all three via _ORDERED_RANKS.
    for _decl_kind, _decls in (("reservation", patch.get("reservations", [])),
                               ("prohibition", patch.get("prohibitions", []))):
        for _d in _decls:
            _g = _d.get("when")
            if not _g:
                continue
            _parts = _g.split()
            if len(_parts) != 3:
                errors.append(f"{_decl_kind} {_d.get('kind')!r}: guard {_g!r} is not a 3-token predicate")
                continue
            _field, _op, _val = _parts
            if _field not in GUARD_FIELDS:
                errors.append(
                    f"{_decl_kind} {_d.get('kind')!r}: guard over {_field!r} forbidden — "
                    f"a guard ranges only over {sorted(GUARD_FIELDS)} (no-id wall)")
            elif _op not in GUARD_OPS[_field]:
                errors.append(f"{_decl_kind} {_d.get('kind')!r}: operator {_op!r} not defined for guard field {_field!r}")
            elif _field in _ORDERED_RANKS and _val not in _ORDERED_RANKS[_field]:
                errors.append(
                    f"{_decl_kind} {_d.get('kind')!r}: {_field} {_val!r} not in "
                    f"{list(_ORDERED_RANKS[_field])}")

    cords = patch.get("cords", [])
    pipe_edges: list[tuple[str, str]] = []
    egress_gates: set[str] = set()
    for c in cords:
        src, dst = c.get("from"), c.get("to")
        # endpoints must be declared (master is implicit)
        if dst != MASTER and dst not in by_id:
            errors.append(f"cord -> {dst!r}: target is not a declared node")
            continue
        if src != MASTER and src not in by_id:
            errors.append(f"cord {src!r} ->: source is not a declared node")
            continue
        # classify by endpoint classes (the only legal pairings)
        if dst == MASTER:
            if src in gates:
                c["type"] = "egress"; egress_gates.add(src)
            elif src in actors:
                errors.append(f"cord {src!r} -> master: an actor must pass through a gate")
            else:
                errors.append(f"cord {src!r} -> master: only a gate egresses to master")
        elif src in actors and dst in gates:
            c["type"] = "authority"
        elif src in gates and dst in gates:
            c["type"] = "pipe"; pipe_edges.append((src, dst))
        elif src in humans:
            errors.append(f"cord {src!r}: a human is never a cord endpoint")
        elif dst in humans:
            errors.append(f"cord -> {dst!r}: a human is never a cord endpoint")
        else:
            errors.append(f"cord {src!r} -> {dst!r}: ill-formed endpoint pairing")

    # exactly one master is implicit; egress cords must exist for a usable graph,
    # but the binding rule we enforce: every gate lies on a pipe∪egress path to master.
    if gates:
        reach = set(egress_gates)
        changed = True
        succ: dict[str, list[str]] = {}
        for a, b in pipe_edges:
            succ.setdefault(a, []).append(b)
        while changed:
            changed = False
            for a, b in pipe_edges:
                if b in reach and a not in reach:
                    reach.add(a); changed = True
        for g in gates:
            if g not in reach:
                errors.append(f"gate {g!r}: not on any pipe/egress path to master")

    # pipe relation must be acyclic
    if _has_cycle(pipe_edges):
        errors.append("pipe relation has a cycle (must be acyclic)")

    # authority: the gate must grant that actor (grant clause or authority cord both count)
    # (authority cords are themselves the grant; nothing further to check here)

    # v0.9.0 consignment: a gate declaring a consignee MUST be terminal (it
    # egresses to the master) — exactly as a required grade on a non-source gate
    # is ill-formed (§6, §7.1). `egress_gates` is the set of gates with an
    # outgoing egress cord, so absence there is sufficient to catch an interior
    # (piped-only) gate that never itself reaches the boundary.
    _consignees: set[str] = set()
    for nd in patch.get("nodes", []):
        if nd["class"] == "gate" and nd.get("consignee"):
            _consignees.add(nd["consignee"])
            if nd["id"] not in egress_gates:
                errors.append(
                    f"gate {nd['id']!r}: consignee {nd['consignee']!r} on a "
                    f"non-terminal gate is ill-formed (§6)")

    # §6/§7.1 autonomy grade (v0.6) — apply stage. A grade must be a level on the active
    # ladder; a REQUIRED grade may sit only on a SOURCE gate (no incoming pipe), since
    # the proposing actor is the recorded cause only there (no identity rides a pipe).
    _piped_to = {b for (_a, b) in pipe_edges}
    _by_id = {nd["id"]: nd for nd in patch.get("nodes", [])}
    for nd in patch.get("nodes", []):
        if nd["class"] == "actor" and nd.get("grade") is not None and nd["grade"] not in GRADE_RANK:
            errors.append(f"actor {nd['id']!r}: grade {nd['grade']!r} not on the ladder {GRADES}")
        if nd["class"] == "gate" and nd.get("grade_required") is not None:
            if nd["grade_required"] not in GRADE_RANK:
                errors.append(f"gate {nd['id']!r}: required grade {nd['grade_required']!r} not on the ladder {GRADES}")
            if nd["id"] in _piped_to:
                errors.append(f"gate {nd['id']!r}: a required grade on a non-source (piped) gate is ill-formed (§6)")
        # delegation may not amplify: a delegate's granted grade may not exceed the
        # delegator's, and an ungraded delegator caps the delegate at ungraded (no
        # grade-from-nothing). Ungraded ranks below L0 (-1), so both cases fall out of
        # one rank comparison. Ranges over actor→actor links only (§6): a human
        # delegator anchors answerability and constrains no grant.
        if nd["class"] == "actor" and nd.get("on_behalf_of"):
            boss = _by_id.get(nd["on_behalf_of"])
            if boss is not None and boss.get("class") == "actor" and nd.get("grade") is not None and \
                    GRADE_RANK.get(nd["grade"], -1) > GRADE_RANK.get(boss.get("grade"), -1):
                errors.append(
                    f"actor {nd['id']!r}: granted grade {nd['grade']!r} amplifies its "
                    f"delegator {boss['id']!r} (grade {boss.get('grade')!r}) — ill-formed")

    # §5.1/§6 the principal chain: the on-behalf-of relation must name a declared
    # actor or human, declare at most one delegator per actor, and be acyclic —
    # each violation is ill-formed at apply (fail-closed). A human delegator
    # anchors answerability and constrains no grant, so the no-amplification
    # checks (grade above, risk below) range over actor→actor links only.
    _obo_edges: list[tuple[str, str]] = []
    for nd in patch.get("nodes", []):
        if nd["class"] != "actor":
            continue
        if nd.get("on_behalf_of_extra"):
            errors.append(
                f"actor {nd['id']!r}: declares more than one delegator — "
                f"at most one on-behalf-of per actor")
        boss_id = nd.get("on_behalf_of")
        if not boss_id:
            continue
        boss = by_id.get(boss_id)
        if boss is None or boss["class"] not in ("actor", "human"):
            errors.append(
                f"actor {nd['id']!r}: on-behalf-of {boss_id!r} does not name a "
                f"declared actor or human")
        elif boss["class"] == "actor":
            _obo_edges.append((nd["id"], boss_id))
    if _has_cycle(_obo_edges):
        errors.append("on-behalf-of relation has a cycle (the principal chain must be acyclic)")

    # v0.9.0 mandate-attenuation invariant (§6): an actor declares at most one
    # mandate, and a delegate's mandate MUST be a subset of its actor-delegator's.
    # A delegator declaring no mandate has the empty set, so its delegate MUST
    # also declare none — an actor cannot confer a purpose it was not itself
    # given. Ranges over actor→actor links only: a human delegator constrains no
    # mandate, exactly as it constrains no grant (above).
    for nd in patch.get("nodes", []):
        if nd["class"] != "actor":
            continue
        if nd.get("mandate_extra"):
            errors.append(
                f"actor {nd['id']!r}: declares more than one mandate — "
                f"at most one per actor")
        boss_id = nd.get("on_behalf_of")
        if not boss_id:
            continue
        boss = by_id.get(boss_id)
        if boss is None or boss.get("class") != "actor":
            continue  # undeclared/human delegator handled above; human constrains no mandate
        delegate_mandate = set(nd.get("mandate") or [])
        boss_mandate = set(boss.get("mandate") or [])
        if not delegate_mandate <= boss_mandate:
            errors.append(
                f"actor {nd['id']!r}: mandate {sorted(delegate_mandate)} widens beyond "
                f"delegator {boss_id!r} ({sorted(boss_mandate)}) — ill-formed")

    # delegation MUST NOT amplify granted authority over a kind's risk set (§6): at every
    # gate where the delegate is granted a kind, the delegate's granted risk set over that
    # kind MUST be a subset of the delegator's over that same kind at that same gate. A
    # delegator holding no grant over a kind at a gate has the empty set there, so any
    # grant to its delegate at that gate over that kind amplifies: a delegate is never
    # granted where its actor-delegator is not. The check ranges over declared grants
    # only; a bare grant spans every kind at every risk level.
    _all_risks = set(RISKS)

    def _risk_set_over(actor_id: str, gate_id: str, kind: str) -> set[str]:
        s: set[str] = set()
        for g in patch.get("grants", []):
            if g.get("gate") != gate_id or g.get("actor") != actor_id:
                continue
            kinds = g.get("kinds") or []
            risks = g.get("risks") or []
            if not kinds:
                return set(_all_risks)                  # bare grant → every kind, every risk
            if kind in kinds:
                s |= (set(risks) if risks else set(_all_risks))
        return s

    for nd in patch.get("nodes", []):
        if nd["class"] != "actor" or not nd.get("on_behalf_of"):
            continue
        sub_id, boss_id = nd["id"], nd["on_behalf_of"]
        _boss_nd = by_id.get(boss_id)
        if _boss_nd is None or _boss_nd["class"] != "actor":
            continue        # undeclared delegator rejected above; a human delegator constrains no grant
        for g in (gr for gr in patch.get("grants", []) if gr.get("actor") == sub_id):
            gate_id = g.get("gate")
            kinds = g.get("kinds") or []
            if not kinds:
                # a bare delegate grant spans every kind at every risk; only the
                # delegator's own bare grant at the same gate covers it
                if not any(bg.get("actor") == boss_id and bg.get("gate") == gate_id
                           and not bg.get("kinds") for bg in patch.get("grants", [])):
                    errors.append(
                        f"actor {sub_id!r}: bare grant at gate {gate_id!r} amplifies "
                        f"delegator {boss_id!r} (no covering bare grant) — ill-formed")
                continue
            risks = g.get("risks") or []
            ds = set(risks) if risks else set(_all_risks)
            for k in kinds:
                bs = _risk_set_over(boss_id, gate_id, k)
                if not ds <= bs:
                    errors.append(
                        f"actor {sub_id!r}: granted risk set {sorted(ds)} over {k!r} at gate "
                        f"{gate_id!r} amplifies delegator {boss_id!r} ({sorted(bs)}) — ill-formed")

    # Apply-stage well-formedness of grants + reservation clauses. These parse fine but
    # reference an undeclared actor or a malformed clause: reject them here, fail-closed,
    # rather than trust a downstream layer to catch — or silently degrade.
    for g in patch.get("grants", []):
        if g.get("actor") not in actors:
            errors.append(
                f"grant to undeclared actor {g.get('actor')!r} at gate {g.get('gate')!r} "
                f"(a grantee must be a declared actor)")
    # SYNTAX §3 (v0.7.0): an obligation attaches to a DECLARED gate. `obligation X on
    # ghost` parses (grammar) but is ill-formed at apply, like every other
    # undeclared-node reference. Fail-closed HERE — before v0.7.0 this was
    # accept-and-deferred: evaluate() withheld at the boundary (an unattached
    # obligation gate never egresses), but the ill-formed graph itself validated ok
    # (the `reject-obligation-undeclared-gate` conformance vector caught this).
    for o in patch.get("obligations", []):
        if o.get("on") not in gates:
            errors.append(
                f"obligation {o.get('obligation')!r} on {o.get('on')!r}: "
                f"the named gate is not a declared gate")
    _DUR_RE = re.compile(r"^\d+[mhd]$")
    for r in patch.get("reservations", []):
        by = (r.get("by") or "").strip()
        qm = re.match(r"^(\d+)\s+of\s+\{(.*)\}$", by)
        if qm:
            n = int(qm.group(1))
            roles = [x.strip() for x in qm.group(2).split(",") if x.strip()]
            if not roles:
                errors.append(f"reserve {r.get('kind')!r}: degenerate quorum {by!r} — empty role set")
            elif n < 1:
                errors.append(f"reserve {r.get('kind')!r}: quorum {by!r} requires at least one hand")
            elif n > len(roles):
                errors.append(
                    f"reserve {r.get('kind')!r}: quorum {by!r} needs {n} of {len(roles)} roles — unsatisfiable")
        d = r.get("duration")
        if d is not None and not _DUR_RE.match(str(d)):
            errors.append(f"reserve {r.get('kind')!r}: bad duration {d!r} (expected e.g. 30d, 2h, 15m)")
        oe = r.get("on_elapse")
        if oe is not None and oe not in ("halt", "proceed"):
            errors.append(f"reserve {r.get('kind')!r}: bad on_elapse {oe!r} (expected 'halt' or 'proceed')")

    # v0.9.0 transfer: a transfer names where a released action's material goes
    # and the purposes it is limited to there (§6). A transfer naming a
    # consignee no gate declares, or with an empty purpose set, is ill-formed —
    # inert rather than silently accepted. The transfer-attenuation invariant
    # applies the mandate rule to this LATERAL relation: for every actor granted
    # over that kind at a gate consigning to that party, the transfer's purposes
    # MUST be a subset of that actor's mandate (an unmandated actor holds the
    # empty set and licenses nothing onward).
    def _actors_granted_over_kind_at(gate_id: str, kind: str) -> set[str]:
        grants_here = [g for g in patch.get("grants", []) if g.get("gate") == gate_id]
        narrowed = {g["actor"] for g in grants_here}
        result = {g["actor"] for g in grants_here if not (g.get("kinds") or []) or kind in (g.get("kinds") or [])}
        for c in patch.get("cords", []):
            if (c.get("type") or _classify(c, by_id)) == "authority" and c.get("to") == gate_id:
                actor = c.get("from")
                if actor not in narrowed:
                    result.add(actor)  # a bare authority cord confers full (every-kind) authority
        return result

    for t in patch.get("transfers", []):
        if t.get("to") not in _consignees:
            errors.append(
                f"transfer {t.get('kind')!r} to {t.get('to')!r}: no gate declares "
                f"this consignee — ill-formed")
            continue
        purposes = set(t.get("within") or [])
        if not purposes:
            errors.append(f"transfer {t.get('kind')!r} to {t.get('to')!r}: empty purpose set — ill-formed")
            continue
        consigning_gates = {nd["id"] for nd in patch.get("nodes", [])
                            if nd["class"] == "gate" and nd.get("consignee") == t["to"]}
        for gate_id in consigning_gates:
            for actor_id in _actors_granted_over_kind_at(gate_id, t["kind"]):
                actor_mandate = set((by_id.get(actor_id) or {}).get("mandate") or [])
                if not purposes <= actor_mandate:
                    errors.append(
                        f"transfer {t['kind']!r} to {t['to']!r}: purposes {sorted(purposes)} "
                        f"exceed the mandate of actor {actor_id!r} ({sorted(actor_mandate)}) "
                        f"granted at gate {gate_id!r} — ill-formed")

    return {"ok": not errors, "errors": errors}


def _has_cycle(edges: list[tuple[str, str]]) -> bool:
    # Iterative depth-first search (explicit stack), not recursion — a deep pipe
    # chain would blow Python's recursion limit and surface as a RecursionError
    # instead of a clean validation result. Standard white/gray/black back-edge
    # detection.
    succ: dict[str, list[str]] = {}
    nodes: set[str] = set()
    for a, b in edges:
        succ.setdefault(a, []).append(b)
        nodes.add(a); nodes.add(b)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {x: WHITE for x in nodes}
    for start in nodes:
        if color[start] != WHITE:
            continue
        color[start] = GRAY
        stack: list[tuple[str, "Any"]] = [(start, iter(succ.get(start, [])))]
        while stack:
            u, it = stack[-1]
            advanced = False
            for v in it:
                if color[v] == GRAY:          # back edge to a node on the stack
                    return True
                if color[v] == WHITE:
                    color[v] = GRAY
                    stack.append((v, iter(succ.get(v, []))))
                    advanced = True
                    break
            if not advanced:
                color[u] = BLACK
                stack.pop()
    return False


# ── projection: patch -> observation (matches a vector's expected.json) ─────────
def _resolved_party(nd: dict[str, Any], by_id: dict[str, Any]) -> Optional[str]:
    """An actor's projected party (§6): its declared party or, for a partyless
    delegate, the nearest declared party along the principal chain; None when no
    party is declared anywhere on the chain. A human declares no party, so a
    chain rooted in a person contributes none from that link. The visited guard
    keeps the walk total on a cyclic chain, which validate() rejects separately."""
    seen: set[str] = set()
    cur: Optional[dict[str, Any]] = nd
    while cur is not None and cur["id"] not in seen:
        if cur.get("party"):
            return cur["party"]
        seen.add(cur["id"])
        cur = by_id.get(cur.get("on_behalf_of") or "")
    return None


def project(patch: dict[str, Any]) -> dict[str, Any]:
    """Project the patch to the externally visible observation, in declaration
    order, with the implicit single master appended."""
    by_id = {nd["id"]: nd for nd in patch.get("nodes", [])}
    out_nodes: list[dict[str, Any]] = []
    for nd in patch.get("nodes", []):
        cls = nd["class"]
        p: dict[str, Any] = {"id": nd["id"], "class": cls}
        if cls == "human" and "role" in nd:
            p["role"] = nd["role"]
        if cls == "actor" and nd.get("grade") is not None:
            p["grade"] = nd["grade"]                     # v0.6 granted autonomy grade
        if cls == "actor" and nd.get("on_behalf_of"):
            p["on_behalf_of"] = nd["on_behalf_of"]       # v0.7: one link of the principal chain
        if cls == "actor" and nd.get("mandate"):
            # v0.9.0: the declared purpose set, projected in ascending
            # lexicographic order (§6, §9) regardless of declaration order.
            p["mandate"] = sorted(set(nd["mandate"]))
        if cls == "gate" and "risk_floor" in nd:
            p["risk_floor"] = nd["risk_floor"]
        if cls == "gate" and nd.get("grade_required") is not None:
            p["grade_required"] = nd["grade_required"]   # v0.6 required grade (source gate)
        if cls == "gate" and nd.get("consignee"):
            p["consignee"] = nd["consignee"]              # v0.9.0: the party this gate's release goes to
        # §9 accountability attribute round-trips; an actor's projected party is
        # resolved along the principal chain (v0.7), a gate's is its declared one
        party = _resolved_party(nd, by_id) if cls == "actor" else nd.get("party")
        if party:
            p["party"] = party
        out_nodes.append(p)
    out_nodes.append({"id": MASTER, "class": "master"})

    # cords: a grant clause (gate line) and an explicit `cord actor -> gate` denote the
    # SAME authority conferral (SYNTAX §3), so the observation records an authority cord
    # for either surface form. Emit the grant-derived authority cords first, in grant-
    # declaration order, then the remaining declared cords — de-duplicating an authority
    # edge a writer expressed both ways (grant clause AND cord line).
    out_cords: list[dict[str, Any]] = []
    seen_auth: set[tuple[str, str]] = set()
    for g in patch.get("grants", []):
        key = (g["actor"], g["gate"])
        if key in seen_auth:
            continue
        seen_auth.add(key)
        out_cords.append({"from": g["actor"], "to": g["gate"], "type": "authority"})
    for c in patch.get("cords", []):
        t = c.get("type") or _classify(c, by_id)
        if t == "authority" and (c["from"], c["to"]) in seen_auth:
            continue
        out_cords.append({"from": c["from"], "to": c["to"], "type": t})

    obs: dict[str, Any] = {"nodes": out_nodes, "cords": out_cords}
    obs["reservations"] = [
        # v0.6: a reservation's temporal clause (duration + on_elapse) is part of the
        # observation — the schema carries them — present only when the reservation
        # declares a duration.
        {**{k: v for k, v in r.items() if k in ("kind", "by", "when")},
         **({"duration": r["duration"], "on_elapse": r.get("on_elapse", "halt")}
            if r.get("duration") else {})}
        for r in patch.get("reservations", [])
    ]
    if patch.get("redress"):
        obs["redress"] = [
            {"kind": r["kind"], "by": r["by"],
             "overturn": bool(r.get("overturn", False)),
             "within": r.get("within")}
            for r in patch["redress"]
        ]
    if patch.get("transfers"):
        # v0.9.0: policy-global, projected as its own ordered member — a
        # transfer belongs to no single node. `within` is a set, projected in
        # ascending lexicographic order like `mandate` (§9).
        obs["transfers"] = [
            {"kind": t["kind"], "to": t["to"], "within": sorted(set(t.get("within") or []))}
            for t in patch["transfers"]
        ]
    return obs


def _classify(c: dict[str, Any], by_id: dict[str, Any]) -> str:
    src, dst = c["from"], c["to"]
    if dst == MASTER:
        return "egress"
    sc = by_id.get(src, {}).get("class")
    dc = by_id.get(dst, {}).get("class")
    if sc == "actor" and dc == "gate":
        return "authority"
    if sc == "gate" and dc == "gate":
        return "pipe"
    return "invalid"


# ── token validation (schema/token.schema.json) ────────────────────────────────
def validate_token(token: Any) -> bool:
    if not isinstance(token, dict):
        return False
    for f in ("id", "kind", "party"):
        if not isinstance(token.get(f), str):
            return False
    if token.get("risk") not in RISK_RANK:
        return False
    prov = token.get("provenance")
    if not isinstance(prov, list) or not all(isinstance(x, str) for x in prov):
        return False
    # tags are OPTIONAL (absent ⇒ treated as empty); when present, a list of strings.
    tags = token.get("tags")
    if tags is not None and (not isinstance(tags, list) or not all(isinstance(x, str) for x in tags)):
        return False
    # v0.9.0: `reversibility` and `uncertainty` are OPTIONAL declared, ordered
    # properties (schema/token.schema.json) — absent is valid (no >= guard ever
    # matches an absent level, §4); when present each MUST be a level on its
    # active scale.
    if "reversibility" in token and token["reversibility"] not in REVERSIBILITY_RANK:
        return False
    if "uncertainty" in token and token["uncertainty"] not in UNCERTAINTY_RANK:
        return False
    return True


# ── §5 transport: evaluate the policy graph for given activations ───────────────
def _guard_holds(guard: Optional[str], token: dict[str, Any], eff_risk: str) -> bool:
    if not guard:
        return True
    parts = guard.split()
    if len(parts) != 3:
        return False
    field, op, val = parts
    if field == "kind" and op == "=":
        return token.get("kind") == val
    if field == "party" and op == "=":
        return token.get("party") == val
    if field in _ORDERED_RANKS:
        ranks = _ORDERED_RANKS[field]
        # `risk` compares the gate-floored effective value (§4: a gate's risk
        # floor raises a token's risk before any guard is tested); `reversibility`
        # and `uncertainty` have no gate floor (§4) and read straight off the
        # token. An absent ordered property ranks below every declared level, so
        # it never satisfies a `>=` guard and matches `=` only against nothing —
        # silence is neither treated as safety nor as danger (SPEC §4).
        tr = ranks.get(eff_risk if field == "risk" else token.get(field), -1)
        vr = ranks.get(val, 10**9)
        if op == ">=":
            return tr >= vr
        if op == "=":
            return tr == vr
    if field == "tags" and op == "contains":
        # membership over a declared set — no computed value (§6). Absent ⇒ false.
        t = token.get("tags")
        return isinstance(t, list) and val in t
    return False


def _authorized(patch: dict[str, Any], gate_id: str, actor: Optional[str],
                kind: Any, eff_risk: str) -> bool:
    """Does `actor` hold an authorizing grant for this token at `gate_id`?

    Authority is conferred by a grant clause — which MAY narrow to particular `kind`
    classes and, over a kind, to a `risk` set (§6) — or by a bare authority cord
    (`cord actor -> gate`, full). With no covering grant the actor is unauthorized and
    §7.1 step (2) assigns `refused`. `actor is None` means no proposing identity is
    present (an interior gate reached over a pipe — no identity rides a pipe), so the
    refused test does not apply there."""
    if actor is None:
        return True
    grants_here = [g for g in patch.get("grants", [])
                   if g.get("gate") == gate_id and g.get("actor") == actor]
    if not grants_here:
        # no grant clause: a bare authority cord (actor -> gate) still confers authority
        by_id = {nd["id"]: nd for nd in patch.get("nodes", [])}
        return any(
            (c.get("type") or _classify(c, by_id)) == "authority"
            and c.get("from") == actor and c.get("to") == gate_id
            for c in patch.get("cords", [])
        )
    for g in grants_here:
        kinds = g.get("kinds") or []
        risks = g.get("risks") or []
        if not kinds:
            return True                                # bare grant → full authority
        if kind in kinds and (not risks or eff_risk in risks):
            return True                                # within the granted kind/risk scope
    return False


def _gate_own_verdict(patch: dict[str, Any], gate_id: str, token: dict[str, Any],
                      actor: Optional[str] = None) -> str:
    gate = next((nd for nd in patch["nodes"] if nd["id"] == gate_id), {})
    floor = gate.get("risk_floor", "low")
    eff_risk = RISKS[max(RISK_RANK.get(token.get("risk", "low"), 0), RISK_RANK.get(floor, 0))]
    kind = token.get("kind")
    # §7.1 assignment priority: prohibited > refused > reserved > auto/human
    for p in patch.get("prohibitions", []):
        if p["kind"] == kind and _guard_holds(p.get("when"), token, eff_risk):
            return "prohibited"
    # step (2): the acting actor holds no authorizing grant at this gate (default-deny).
    # refused pre-empts reserved here, though the join (§7.2) orders them the other way.
    if not _authorized(patch, gate_id, actor, kind, eff_risk):
        return "refused"
    for r in patch.get("reservations", []):
        if r["kind"] == kind and _guard_holds(r.get("when"), token, eff_risk):
            return "reserved"
    # non-reserved, non-prohibited: `auto` is the step-(4) disposition — normative
    # as of v0.7.0 (SPEC §7.1); a gate declaring no required grade disposes auto.
    return "auto"


def _join(a: str, b: str) -> str:
    return a if VERDICT_RANK[a] >= VERDICT_RANK[b] else b


def evaluate(patch: dict[str, Any], transport: dict[str, Any]) -> dict[str, Any]:
    """Evaluate activations -> {gate: {verdict, [master: act|withhold]}}.

    Each activation enters at a source gate; the effective verdict joins
    strictest-wins along pipes to the terminal gate; the master acts iff the
    terminal effective verdict is auto and every egress obligation is attached.
    """
    result, _ = _evaluate_with_log(patch, transport)
    return result


def evaluate_log(patch: dict[str, Any], transport: dict[str, Any]) -> list[dict[str, str]]:
    """The §7.4 log trace: one entry per activated gate, in evaluation order,
    each carrying that gate's effective verdict (§7.2 join), as {gate, verdict}.
    The presence and ordering of these entries is part of the observation and
    conformance-tested; a missing or misordered entry is itself a failure."""
    _, log = _evaluate_with_log(patch, transport)
    return log


def _evaluate_with_log(
    patch: dict[str, Any], transport: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    # pipe successors and egress set
    succ: dict[str, str] = {}
    egress: set[str] = set()
    for c in patch.get("cords", []):
        t = c.get("type") or _classify(c, {nd["id"]: nd for nd in patch["nodes"]})
        if t == "pipe":
            succ[c["from"]] = c["to"]
        elif t == "egress":
            egress.add(c["from"])
    oblig_gates = {o["on"] for o in patch.get("obligations", [])}
    # The master releases an `auto` action only if every egress obligation is
    # attached — i.e. every declared obligation sits on a gate that actually
    # egresses to the master (a real point of attachment). An obligation whose gate
    # never reaches the boundary cannot be borne by any released action, so the
    # boundary withholds (fail-closed): this is computed from the graph, never
    # assumed true.
    obligations_attached = oblig_gates.issubset(egress)

    by_id = {nd["id"]: nd for nd in patch.get("nodes", [])}
    result: dict[str, Any] = {}
    log: list[dict[str, str]] = []
    for act in transport.get("activations", []):
        token = act["token"]
        cur = act["source"]
        eff = _gate_own_verdict(patch, cur, token, act.get("actor"))
        # v0.6 §7.1 step-(4): at the SOURCE gate the auto/human disposition is gated by
        # grade when the gate declares a required grade R. Only an 'auto' own verdict is
        # graded — prohibited/refused/reserved keep precedence (steps 1-3). G≥R ⇒ auto;
        # G<R or an ungraded proposing actor ⇒ human (fail-closed); no R ⇒ unchanged.
        R = (by_id.get(cur) or {}).get("grade_required")
        if eff == "auto" and R is not None:
            G = (by_id.get(act.get("actor")) or {}).get("grade")
            if not grade_meets(G, R):       # shared authority — same rule the app run-path uses
                eff = "human"
        # record source gate's own verdict (its effective verdict: no predecessor)
        result.setdefault(cur, {})["verdict"] = eff
        log.append({"gate": cur, "verdict": eff})
        # propagate along the pipe chain to the terminal gate; each activated
        # gate logs its effective verdict (§7.4), in evaluation order
        while cur in succ:
            nxt = succ[cur]
            own = _gate_own_verdict(patch, nxt, token)
            eff = _join(eff, own)
            result.setdefault(nxt, {})["verdict"] = eff
            log.append({"gate": nxt, "verdict": eff})
            cur = nxt
        # cur is terminal; if it egresses, the master decides
        if cur in egress:
            release = (eff == "auto") and obligations_attached
            result.setdefault(cur, {})["master"] = "act" if release else "withhold"
    return result, log


# ── writer: patch -> .lg netlist (canvas/editor/ingest -> text) ──────────────
def to_netlist(patch: dict[str, Any]) -> str:
    """Serialize a patch back to the textual surface. parse(to_netlist(p)) is the
    round-trip; the grammar requires `grant` last on a gate line."""
    lines: list[str] = []
    grants = patch.get("grants", [])

    def _grade_tok(g: Any) -> str:
        # the netlist is the LANGUAGE surface ("L0".."L4"); normalise an app-layer
        # integer rank to its ladder string so parse(to_netlist(p)) round-trips and
        # never emits a bare int that would reparse as an invalid grade token.
        if isinstance(g, int) and not isinstance(g, bool) and 0 <= g <= _GRADE_MAX_RANK:
            return GRADES[g]
        return str(g)
    def _grant_tok(g: dict[str, Any]) -> str:
        a = g["actor"]
        kinds = g.get("kinds") or []
        risks = g.get("risks") or []
        if kinds and risks:
            return f"{a}[{','.join(kinds)}:{','.join(risks)}]"
        if kinds:
            return f"{a}[{','.join(kinds)}]"
        return a

    def _purpose_tok(purposes: Any) -> str:
        # v0.9.0: a single purpose may be written bare; a set needs braces.
        ps = list(purposes)
        if len(ps) == 1:
            return ps[0]
        return "{" + ",".join(ps) + "}"

    for n in patch.get("nodes", []):
        cls = n.get("class")
        if cls == "actor":
            s = "actor " + n["id"]
            if n.get("party"):
                s += " party " + n["party"]
            if n.get("on_behalf_of"):
                s += " on-behalf-of " + n["on_behalf_of"]
            if n.get("grade"):
                s += " grade " + _grade_tok(n["grade"])       # normalise int rank → "Lk" for the language surface
            if n.get("mandate"):
                s += " mandate " + _purpose_tok(n["mandate"])  # v0.9.0 declared purpose set
            if n.get("name"):                                 # name consumes the rest of the line; keep it last
                s += " name " + n["name"]
            lines.append(s)
        elif cls == "human":
            s = "human " + n["id"]
            if n.get("role"):
                s += " role " + n["role"]
            if n.get("name"):
                s += " name " + n["name"]
            lines.append(s)
        elif cls == "gate":
            s = "gate " + n["id"]
            if n.get("risk_floor"):
                s += " risk " + n["risk_floor"]
            if n.get("party"):
                s += " party " + n["party"]
            if n.get("grade_required"):
                s += " grade " + _grade_tok(n["grade_required"])   # normalise int rank → "Lk"
            if n.get("consignee"):
                s += " consign " + n["consignee"]              # v0.9.0: the party this gate's release goes to
            if n.get("name") and " " not in str(n["name"]):   # gate name is a single token (grammar)
                s += " name " + n["name"]
            gs = [g for g in grants if g.get("gate") == n["id"]]
            if gs:                              # grant clause MUST be last on the line
                s += " grant " + " ".join(_grant_tok(g) for g in gs)
            lines.append(s)
    for r in patch.get("reservations", []):
        s = "reserve " + r["kind"] + " by " + r["by"]
        if r.get("when"):
            s += " when " + r["when"]
        if r.get("duration") and r.get("on_elapse"):
            s += " duration " + r["duration"] + " : " + r["on_elapse"]
        lines.append(s)
    for pr in patch.get("prohibitions", []):
        s = "prohibit " + pr["kind"]
        if pr.get("when"):
            s += " when " + pr["when"]
        lines.append(s)
    for o in patch.get("obligations", []):
        lines.append("obligation " + o["obligation"] + " on " + o["on"])
    for rd in patch.get("redress", []):
        s = "redress " + rd["kind"] + " by " + rd["by"]
        if rd.get("overturn"):
            s += " overturn"
        if rd.get("within"):
            s += " within " + rd["within"]
        lines.append(s)
    for t in patch.get("transfers", []):
        lines.append("transfer " + t["kind"] + " to " + t["to"] + " within " + _purpose_tok(t["within"]))
    for c in patch.get("cords", []):
        lines.append("cord " + c["from"] + " -> " + c["to"])
    return "\n".join(lines) + "\n"


def apply(source_or_patch) -> dict[str, Any]:
    """Parse and validate a Loomground program, failing closed at apply stage."""
    patch = parse(source_or_patch) if isinstance(source_or_patch, str) else source_or_patch
    report = validate(patch)
    if not report["ok"]:
        raise ApplyError(report["errors"])
    return patch


def reason(source_or_patch, transport: Optional[dict[str, Any]] = None,
           risk_table: Optional[Any] = None) -> dict[str, Any]:
    """Run Loomground as a Solver nD route.

    The generic partitions retain the richer language verdicts in ``trace``:
    ``auto`` actions are accepted, ``human``/``reserved`` actions are undecided,
    and ``refused``/``prohibited`` actions are rejected.

    ``risk_table`` is an OPTIONAL ``prom001.GovernedRiskTable`` (PROM-001,
    v0.11.0, §4/§7.4): when supplied, an activation carrying an ``observed``
    host-observation dict is governed BEFORE evaluate() sees it — its `kind`
    becomes host-observed (never the actor's claim), its `risk` is
    gate-computed from the table with a self-declared hint admitted only as a
    raise-only ratchet, and an unclassifiable observation or a declared/
    observed mismatch floors it to the strictest tier. Absent `risk_table` (the
    default), or an activation with no `observed` key, behaviour is
    byte-for-byte unchanged from before PROM-001 — this is a strictly additive
    capability, never a silent reinterpretation of an existing token. The dual
    log — both the declared token and the host-observed facts, per activation —
    lands in ``trace["prom001"]`` (§7.4); it is solver-internal and is not part
    of the language's own observation/log schemas.
    """
    patch = apply(source_or_patch)
    observation = project(patch)
    transport = dict(transport or {"activations": []})

    prom001_log: list[dict[str, Any]] = []
    if risk_table is not None:
        from .prom001 import HostObservation, govern_token  # deferred: avoids a module cycle

        governed_activations = []
        for act in transport.get("activations", []):
            observed = act.get("observed")
            if observed is None:
                governed_activations.append(act)
                continue
            host_observation = HostObservation(
                kind=observed.get("kind"), target=observed.get("target", ""),
                context=observed.get("context", ""), grade=observed.get("grade"),
            )
            governed = govern_token(act.get("token") or {}, host_observation, risk_table)
            prom001_log.append({
                "activation": (act.get("token") or {}).get("id"),
                "declared": governed.declared,
                "observed": governed.observed,
                "kind": governed.kind,
                "risk": governed.risk,
                "floored": governed.floored,
                "floor_reason": governed.floor_reason,
            })
            governed_activations.append({**act, "token": governed.token})
        transport = {**transport, "activations": governed_activations}

    evaluation = evaluate(patch, transport)
    log = evaluate_log(patch, transport)
    accepted, undecided, rejected = [], [], {}

    for index, activation in enumerate(transport.get("activations", [])):
        token = activation.get("token") or {}
        action_id = str(token.get("id") or f"activation-{index + 1}")
        single = evaluate(patch, {"activations": [activation]})
        terminals = [
            (gate, outcome) for gate, outcome in single.items()
            if "master" in outcome
        ]
        if any(outcome.get("master") == "act" for _gate, outcome in terminals):
            accepted.append(action_id)
            continue
        verdicts = [outcome.get("verdict") for _gate, outcome in terminals]
        verdict = max(
            (v for v in verdicts if v in VERDICT_RANK),
            key=VERDICT_RANK.get,
            default="refused",
        )
        if verdict in ("human", "reserved"):
            undecided.append(action_id)
        else:
            rejected[action_id] = verdict

    trace: dict[str, Any] = {
        "observation": observation,
        "evaluation": evaluation,
        "log": log,
    }
    if prom001_log:
        trace["prom001"] = prom001_log

    return {
        "method": "loomground",
        "language": "loomground",
        "language_version": LANGUAGE_VERSION,
        "status": "escalate" if undecided else "complete",
        "accepted": sorted(accepted),
        "undecided": sorted(undecided),
        "rejected": dict(sorted(rejected.items())),
        "trace": trace,
    }


def require_language_version(version: str) -> str:
    """Validate a requested language version without silently upgrading it."""
    requested = str(version or LANGUAGE_VERSION)
    if requested not in SUPPORTED_LANGUAGE_VERSIONS:
        raise ValueError(
            f"unsupported Loomground version {requested!r}; "
            f"supported: {SUPPORTED_LANGUAGE_VERSIONS}"
        )
    return requested
