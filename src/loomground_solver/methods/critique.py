# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Methodology / test methods — philosophy of science and mathematics: evaluate
a hypothesis or a fact set rather than derive from it.

  * falsification (Popper) — does the evidence contradict a rule's prediction?
  * consistency / reductio (mathematics) — is the fact set free of contradiction?
  * hypothetico_deductive — does a hypothesis's prediction survive the evidence?
"""
from __future__ import annotations

from ..subsumption import neg, holds, subsume
from . import register_method


def falsification(facts, rules=(), **_):
    """Popper: a rule is FALSIFIED when its antecedent holds (so it predicts its
    consequence) yet the negation of that consequence is in the evidence. Returns
    the falsified rules and their counterexamples — the corroborated ones survive,
    never 'proven'."""
    fs = set(facts)
    falsified, corroborated = [], []
    for r in rules:
        if not r.consequence:
            continue
        s = subsume(r, fs)
        if s.applicable and holds(neg(r.consequence), fs):
            falsified.append({"rule": r.id, "predicted": r.consequence,
                              "observed": neg(r.consequence)})
        elif s.applicable and holds(r.consequence, fs):
            corroborated.append(r.id)
    return {"falsified": [f["rule"] for f in falsified],
            "counterexamples": falsified, "corroborated": corroborated,
            "any_falsified": bool(falsified)}


def consistency(facts, **_):
    """Mathematics (reductio basis): the fact set is inconsistent iff it contains
    a literal and its negation. Returns the clashing atoms."""
    fs = set(facts)
    clashes = sorted({f.lstrip("-") for f in fs if neg(f) in fs})
    return {"consistent": not clashes, "clashes": clashes}


def hypothetico_deductive(facts, rules=(), *, hypothesis=None, **_):
    """Philosophy of science: assume ``hypothesis`` (a literal), derive what the
    rules then predict, and check whether any prediction is contradicted by the
    evidence. ``supported`` iff a prediction is confirmed and none refuted."""
    fs = set(facts)
    if hypothesis:
        fs = fs | {hypothesis}
    predicted, refuted, confirmed = [], [], []
    for r in rules:
        if r.consequence and subsume(r, fs).applicable:
            predicted.append(r.consequence)
            if holds(neg(r.consequence), set(facts)):
                refuted.append(r.consequence)
            elif holds(r.consequence, set(facts)):
                confirmed.append(r.consequence)
    return {"predicted": sorted(set(predicted)),
            "confirmed": sorted(set(confirmed)),
            "refuted": sorted(set(refuted)),
            "supported": bool(confirmed) and not refuted}


register_method("falsification", "test", falsification)
register_method("consistency", "test", consistency)
register_method("hypothetico_deductive", "test", hypothetico_deductive)
