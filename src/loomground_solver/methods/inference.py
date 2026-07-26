# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Inference methods — logic, philosophy, and data-science styles of deriving
new content from given content. Each returns ``{"facts": [...], "rules": [...]}``.

Logic:   modus_ponens, modus_tollens, hypothetical_syllogism, disjunctive_syllogism
Philos.: abduction (inference to best explanation), analogical_inference
Data:    inductive_generalization
"""
from __future__ import annotations

from ..subsumption import Rule, neg, holds, subsume
from . import register_method


def _out(facts=None, rules=None):
    return {"facts": list(facts or []), "rules": list(rules or [])}


def modus_ponens(facts, rules=()):
    """Deduction: an applicable rule fires its consequence (P, P→Q ⊢ Q)."""
    fs = set(facts)
    return _out(facts=[r.consequence for r in rules
                       if r.consequence and r.consequence not in fs
                       and subsume(r, fs).applicable])


def modus_tollens(facts, rules=()):
    """Deduction: if a single-antecedent rule's consequence is denied, deny the
    antecedent (P→Q, ¬Q ⊢ ¬P)."""
    fs = set(facts)
    out = []
    for r in rules:
        if len(r.conditions) == 1 and r.consequence:
            if holds(neg(r.consequence), fs) and neg(r.conditions[0]) not in fs:
                out.append(neg(r.conditions[0]))
    return _out(facts=out)


def hypothetical_syllogism(facts, rules=()):
    """Deduction: chain implications (P→Q, Q→R ⊢ P→R) — derives new RULES."""
    out = []
    for a in rules:
        for b in rules:
            if a.consequence and a.consequence in b.conditions and len(b.conditions) == 1:
                out.append(Rule(id=f"{a.id}∘{b.id}", conditions=a.conditions,
                                consequence=b.consequence))
    return _out(rules=out)


def disjunctive_syllogism(facts, rules=()):
    """Deduction: from a disjunction ``"x|y"`` and ¬x, derive y (and vice-versa)."""
    fs = set(facts)
    out = []
    for f in fs:
        if "|" in f and not f.startswith("-"):
            x, y = f.split("|", 1)
            if neg(x) in fs and y not in fs:
                out.append(y)
            if neg(y) in fs and x not in fs:
                out.append(x)
    return _out(facts=out)


def abduction(facts, rules=()):
    """Philosophy: inference to the best explanation. For each observed
    consequence, the candidate antecedents that would explain it, ranked by
    parsimony (fewest unmet conditions). Returns candidate facts tagged ``?`` —
    defeasible proposals to be verified downstream, never asserted."""
    fs = set(facts)
    cands = []
    for r in rules:
        if r.consequence in fs and r.conditions:
            missing = [c for c in r.conditions if not holds(c, fs)]
            if missing:
                cands.append((len(missing), tuple(missing), r.id))
    cands.sort()
    best = []
    for _n, missing, _rid in cands:
        for c in missing:
            tag = "?" + c
            if tag not in best:
                best.append(tag)
    return _out(facts=best)


def analogical_inference(facts, rules=(), *, mapping=None, source_relations=()):
    """Philosophy: transfer relational structure across a mapping. Given
    ``source_relations`` as ``(a, rel, b)`` triples and a ``mapping`` a→a', b→b',
    derive the aligned target relations ``(a', rel, b')`` — structure carried,
    surface dropped (Gentner-style, systematicity is the caller's to score)."""
    m = mapping or {}
    out = []
    for (a, rel, b) in source_relations:
        if a in m and b in m:
            out.append(f"{m[a]}:{rel}:{m[b]}")
    return _out(facts=out)


def inductive_generalization(observations, *, min_support=2):
    """Data science: from instances ``(subject, P, Q)`` induce the defeasible
    rule P(x) ⇒ Q(x) with support and confidence; returns the rule plus its
    confidence. ``observations``: list of ``{"x", "p": bool, "q": bool}``."""
    p_true = [o for o in observations if o.get("p")]
    support = len(p_true)
    hits = sum(1 for o in p_true if o.get("q"))
    conf = hits / support if support else 0.0
    rules = []
    if support >= min_support and conf > 0.0:
        rules.append(Rule(id="induced:P->Q", conditions=("P",), consequence="Q"))
    return {"facts": [], "rules": rules, "support": support,
            "confidence": round(conf, 6)}


register_method("modus_ponens", "inference", modus_ponens)
register_method("modus_tollens", "inference", modus_tollens)
register_method("hypothetical_syllogism", "inference", hypothetical_syllogism)
register_method("disjunctive_syllogism", "inference", disjunctive_syllogism)
register_method("abduction", "inference", abduction)
register_method("analogical_inference", "inference", analogical_inference)
register_method("inductive_generalization", "inference", inductive_generalization)
