# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Subsumption — does a rule's conditions hold in the facts? (rung 3, the missing
half of full rule reasoning).

Production-grade rule reasoning is four moves: extract → **subsume** → apply → resolve.
The solver already had apply (forward chaining), resolve (grounded defeasibility),
and the contract. This module adds the *Subsumtion* step — checking a rule's
antecedent (the Tatbestand) against the case facts before its consequent (the
Rechtsfolge) may fire — so the whole pipeline runs standalone.

Representation. A **literal** is a string; ``"-x"`` negates ``"x"``. Facts are a
set of literals under a closed-world default (an unproven condition does not
hold). A :class:`Rule` is ``conditions → consequence`` with optional
``exceptions`` (Ausnahme) and, for norm reasoning, a deontic ``modality`` on an
``act``. Subsumption is **deterministic-first**: a condition is decided by the
facts; only when it is neither present nor negated is an injected ``judge``
(a model, per the ModelFn discipline) consulted — verified, never trusted blind.

Pure stdlib. No governance, no domain."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


def neg(lit: str) -> str:
    """Negate a literal: ``x`` ↔ ``-x``."""
    return lit[1:] if lit.startswith("-") else "-" + lit


@dataclass(frozen=True)
class Rule:
    id: str
    conditions: tuple = ()       # the Tatbestand — literals that must hold
    consequence: str = ""        # the Rechtsfolge — the literal fired
    exceptions: tuple = ()       # the Ausnahme — literals that, if present, block
    # norm-reasoning extras (a deontic rule fires a modality on an act):
    modality: str = ""           # 'obligatory' | 'permitted' | 'prohibited' | ''
    act: str = ""
    source: str = ""
    rank: int = 0
    specificity: int = 0
    time: int = 0


@dataclass
class Subsumption:
    rule: str
    applicable: bool
    satisfied: tuple             # conditions that hold
    missing: tuple               # conditions that do not hold (why it didn't fire)
    blocked_by: tuple            # exceptions that fired (the norm was read to the end)


Judge = Callable[[str, set], bool]     # (literal, facts) -> holds? (model escalation)


def holds(lit: str, facts: set, *, judge: Optional[Judge] = None) -> bool:
    """Closed-world with optional escalation: present ⇒ True; negation present ⇒
    False; otherwise ask ``judge`` if given, else False (unproven ≠ true)."""
    if lit in facts:
        return True
    if neg(lit) in facts:
        return False
    if judge is not None:
        return bool(judge(lit, facts))
    return False


def subsume(rule: Rule, facts: set, *, judge: Optional[Judge] = None) -> Subsumption:
    """Check ``rule`` against ``facts``. Applicable iff every condition holds and
    no exception fires — exceptions examined, never absorbed (norm read to the end)."""
    sat = tuple(c for c in rule.conditions if holds(c, facts, judge=judge))
    missing = tuple(c for c in rule.conditions if c not in sat)
    blocked = tuple(x for x in rule.exceptions if holds(x, facts, judge=judge))
    return Subsumption(rule.id, (not missing) and (not blocked), sat, missing, blocked)


def applicable_rules(rules, facts: set, *, judge: Optional[Judge] = None) -> list:
    return [r for r in rules if subsume(r, facts, judge=judge).applicable]


def apply(rules, facts: set, *, judge: Optional[Judge] = None,
          max_rounds: int = 1000) -> set:
    """Forward-chain the DESCRIPTIVE rules (no deontic modality) to a fixpoint:
    an applicable rule's consequence is added to the facts, defeasibly (an
    exception blocks it). Deontic rules are NOT chained (a norm is not a fact) —
    collect them with :func:`to_norms`."""
    derived = set(facts)
    changed, rounds = True, 0
    while changed and rounds < max_rounds:
        changed, rounds = False, rounds + 1
        for r in rules:
            if r.modality:
                continue                      # deontic: not a descriptive fact
            if not r.consequence or r.consequence in derived:
                continue
            if subsume(r, derived, judge=judge).applicable:
                derived.add(r.consequence)
                changed = True
    return derived


def to_norms(rules, facts: set, *, judge: Optional[Judge] = None) -> list:
    """Bridge: every APPLICABLE deontic rule becomes a :class:`scenario.Norm`
    (its Tatbestand subsumed), ready for grounded conflict resolution."""
    from .scenario import Norm
    out = []
    for r in rules:
        if r.modality and subsume(r, facts, judge=judge).applicable:
            out.append(Norm(r.act or r.consequence, r.modality, r.source,
                            r.rank, r.specificity, r.time))
    return out


def solve(rules, facts, *, pack=None, judge: Optional[Judge] = None):
    """End-to-end rule reasoning: expand facts (descriptive chaining) → subsume
    the deontic rules → resolve their conflicts (grounded defeasibility under
    ``pack``). Returns a :class:`scenario.ScenarioResult` — feed it to the
    contract / decision space / replay like any derivation."""
    from .scenario import Scenario, derive
    from .rulepacks import GENERIC_PACK
    expanded = apply(rules, set(facts), judge=judge)
    norms = to_norms(rules, expanded, judge=judge)
    return derive(Scenario("rules", norms=norms), pack=pack or GENERIC_PACK)
