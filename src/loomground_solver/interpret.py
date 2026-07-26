# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Interpret — the LLM-interpretation bridge: read an LLM's stated reasoning and
audit it *in a solver way* (rung 3, the language→structure seam).

An LLM reasons in prose; the solver reasons in structure. This module bridges
the two. A model (or the built-in parser) turns a short notation into facts,
rules and a candidate conclusion; the auditor then maps that reasoning onto the
existing machinery — forward chaining, consistency, falsification — and *checks*
it. A hallucinated conclusion (a claim the model's own stated premises do not
entail) comes back with verdict ``"unsound"`` and a reason: the solver catching
an LLM leap.

Notation the built-in parser reads (one statement per line; blank lines and
lines beginning with ``#`` are ignored, whitespace-tolerant):

  * ``fact: X``                 — a literal ``X`` (``-x`` negates; ``a|b`` is a
                                  disjunction literal);
  * ``rule: A, B => C``         — ``Rule(conditions=(A, B), consequence=C)``;
  * ``rule: A => C ! E1, E2``   — the same with ``exceptions=(E1, E2)``;
  * ``claim: S`` / ``therefore: S`` — the candidate conclusion ``S``.

Rule ids are auto-assigned ``r1, r2, …``.

DETERMINISTIC-FIRST. :func:`interpret` uses an injected ``parse`` callable (an
LLM) only when given; otherwise it uses the built-in parser — mirroring the
judge / ModelFn escalation discipline (structure first, model only when needed).

Pure stdlib. No governance, no domain."""
from __future__ import annotations

from .subsumption import Rule, apply as forward_chain
from .methods import method


def _split_conditions(text: str) -> tuple:
    return tuple(c.strip() for c in text.split(",") if c.strip())


def _parse_rule(body: str, rid: str) -> Rule:
    """Parse the body of a ``rule:`` line (everything after the prefix)."""
    conds_part, _, cons_part = body.partition("=>")
    consequence, _, exc_part = cons_part.partition("!")
    return Rule(
        id=rid,
        conditions=_split_conditions(conds_part),
        consequence=consequence.strip(),
        exceptions=_split_conditions(exc_part),
    )


def _builtin_parse(text: str) -> dict:
    """The default parser: notation → ``{facts, rules, candidate}``."""
    facts: set = set()
    rules: list = []
    candidate = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        prefix, sep, body = line.partition(":")
        if not sep:
            continue
        prefix = prefix.strip().lower()
        body = body.strip()
        if prefix == "fact":
            if body:
                facts.add(body)
        elif prefix == "rule":
            rules.append(_parse_rule(body, f"r{len(rules) + 1}"))
        elif prefix in ("claim", "therefore"):
            candidate = body or None
    return {"facts": facts, "rules": rules, "candidate": candidate}


def interpret(text, *, parse=None) -> dict:
    """Interpret ``text`` into ``{"facts", "rules", "candidate"}``.

    Deterministic-first: if ``parse`` (an injected ``text -> {facts, rules,
    candidate}`` callable, i.e. an LLM) is given it is used; otherwise the
    built-in parser reads the notation. The result is normalised so downstream
    audit always sees a ``set`` of facts, a ``list`` of rules and a candidate
    (``str`` or ``None``)."""
    out = parse(text) if parse is not None else _builtin_parse(text)
    facts = set(out.get("facts") or ())
    rules = list(out.get("rules") or ())
    candidate = out.get("candidate")
    return {"facts": facts, "rules": rules, "candidate": candidate}


def audit(interp) -> dict:
    """Map interpreted reasoning onto the solver and check it.

    Runs forward chaining to a closure, tests the closure for consistency, runs
    falsification over the stated rules, and checks whether the candidate
    conclusion is entailed by the closure. The verdict is ``"sound"`` only when
    the premises are consistent, the candidate is entailed, and no rule is
    falsified — otherwise ``"unsound"`` with human-readable reasons."""
    facts = set(interp.get("facts") or ())
    rules = list(interp.get("rules") or ())
    candidate = interp.get("candidate")

    closure = forward_chain(rules, facts)
    cons = method("consistency")(closure)
    consistent = cons["consistent"]
    fals = method("falsification")(facts, rules)
    entailed = candidate is None or candidate in closure
    unwarranted = [candidate] if (candidate is not None and not entailed) else []

    reasons = []
    if not consistent:
        clashes = cons["clashes"]
        reasons.append(
            "premise set is inconsistent (clashing atoms: "
            + ", ".join(clashes) + ")"
        )
    if candidate is not None and not entailed:
        reasons.append(
            f"conclusion {candidate!r} is not entailed by the stated premises "
            "(unwarranted leap)"
        )
    if fals["any_falsified"]:
        reasons.append(
            "rule(s) falsified by the evidence: "
            + ", ".join(fals["falsified"])
        )
    if not reasons:
        reasons.append("premises consistent, conclusion entailed, no rule falsified")

    verdict = (
        "sound"
        if (consistent and entailed and not fals["any_falsified"])
        else "unsound"
    )
    return {
        "consistent": consistent,
        "entailed": entailed,
        "falsified": fals["falsified"],
        "unwarranted": unwarranted,
        "verdict": verdict,
        "reasons": reasons,
        "closure": sorted(closure),
    }


def audit_text(text, *, parse=None) -> dict:
    """Convenience: :func:`interpret` then :func:`audit` in one call."""
    return audit(interpret(text, parse=parse))
