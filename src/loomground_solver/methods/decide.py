# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Decision methods — rationalist decision theory, mathematics, data science.

These close the decision space deterministically when you have a valuation: given
options and a payoff structure, they return ``{"choice", "ranking", "scores"}``.
This is the deterministic complement to an LLM choosing within ``undecided`` — a
NAMED rational-choice rule instead of a guess.

Under uncertainty (payoff matrix ``{option: {state: value}}``):
    maximin (Wald), maximax, hurwicz(α), minimax_regret (Savage).
Under risk (probabilities over states):
    expected_utility (Bayes/Savage) — with bayesian_update to form the posterior.
Multi-criteria (vectors ``{option: [c1, c2, …]}``):
    pareto (dominance frontier), lexicographic (priority order).
Bounded rationality:
    satisficing (Simon) — first option meeting an aspiration level.
"""
from __future__ import annotations

from . import register_method


def _rank(scores: dict, *, higher_better=True):
    order = sorted(scores, key=lambda o: scores[o], reverse=higher_better)
    return {"choice": order[0] if order else None,
            "ranking": order,
            "scores": {k: round(float(v), 6) for k, v in scores.items()}}


def _states(payoffs):
    return sorted({s for row in payoffs.values() for s in row})


def maximin(options=None, payoffs=None, **_):
    """Wald: choose the option whose WORST outcome is best (pessimism)."""
    payoffs = payoffs or {}
    return _rank({o: min(row.values()) for o, row in payoffs.items() if row})


def maximax(options=None, payoffs=None, **_):
    """Choose the option whose BEST outcome is best (optimism)."""
    payoffs = payoffs or {}
    return _rank({o: max(row.values()) for o, row in payoffs.items() if row})


def hurwicz(options=None, payoffs=None, *, alpha=0.5, **_):
    """Hurwicz: α·best + (1-α)·worst — tune optimism with α∈[0,1]."""
    payoffs = payoffs or {}
    return _rank({o: alpha * max(row.values()) + (1 - alpha) * min(row.values())
                  for o, row in payoffs.items() if row})


def minimax_regret(options=None, payoffs=None, **_):
    """Savage: minimise the maximum REGRET (best-in-state minus your outcome)."""
    payoffs = payoffs or {}
    states = _states(payoffs)
    best_in_state = {s: max(payoffs[o].get(s, float("-inf")) for o in payoffs)
                     for s in states}
    regret = {o: max(best_in_state[s] - payoffs[o].get(s, best_in_state[s])
                     for s in states) for o in payoffs}
    return _rank(regret, higher_better=False)   # minimise regret


def expected_utility(options=None, payoffs=None, *, probabilities=None, **_):
    """Bayes/Savage: maximise Σ P(state)·utility(option, state)."""
    payoffs = payoffs or {}
    probs = probabilities or {}
    if not probs:                               # uniform prior if none given
        states = _states(payoffs)
        probs = {s: 1.0 / len(states) for s in states} if states else {}
    eu = {o: sum(probs.get(s, 0.0) * v for s, v in row.items())
          for o, row in payoffs.items()}
    return _rank(eu)


def bayesian_update(*, prior=None, likelihoods=None, evidence=None, **_):
    """Data science: posterior P(h|e) ∝ P(e|h)·P(h). ``prior``: {hypothesis: p};
    ``likelihoods``: {hypothesis: {evidence: p}}; ``evidence``: the observed key.
    Returns the normalised posterior as ``scores`` (choice = MAP hypothesis)."""
    prior = prior or {}
    likelihoods = likelihoods or {}
    unnorm = {h: prior.get(h, 0.0) * likelihoods.get(h, {}).get(evidence, 0.0)
              for h in prior}
    z = sum(unnorm.values())
    post = {h: (v / z if z else 0.0) for h, v in unnorm.items()}
    return _rank(post)


def pareto(options=None, vectors=None, **_):
    """Mathematics: the Pareto frontier — options not dominated on every
    criterion by another (higher = better on each). ``choice`` = a frontier
    member; ``ranking`` lists the frontier first."""
    vectors = vectors or {}
    def dominates(a, b):
        return (all(x >= y for x, y in zip(a, b))
                and any(x > y for x, y in zip(a, b)))
    frontier = [o for o in vectors
                if not any(dominates(vectors[q], vectors[o])
                           for q in vectors if q != o)]
    rest = [o for o in vectors if o not in frontier]
    return {"choice": frontier[0] if frontier else None,
            "ranking": sorted(frontier) + sorted(rest),
            "scores": {o: (1.0 if o in frontier else 0.0) for o in vectors}}


def lexicographic(options=None, vectors=None, *, order=None, **_):
    """Mathematics: rank by the first criterion; ties broken by the next, etc.
    ``order``: indices of criteria by priority (default: left to right)."""
    vectors = vectors or {}
    if not vectors:
        return {"choice": None, "ranking": [], "scores": {}}
    width = len(next(iter(vectors.values())))
    order = order or list(range(width))
    ranking = sorted(vectors, key=lambda o: tuple(-vectors[o][i] for i in order))
    return {"choice": ranking[0], "ranking": ranking,
            "scores": {o: list(vectors[o]) for o in vectors}}


def satisficing(options=None, valuations=None, *, aspiration=0.0, **_):
    """Simon: bounded rationality — accept the FIRST option meeting the
    aspiration level; ``choice`` is None if none suffices (→ keep searching)."""
    valuations = valuations or {}
    good = [o for o in (options or list(valuations))
            if valuations.get(o, float("-inf")) >= aspiration]
    return {"choice": good[0] if good else None, "ranking": good,
            "scores": {o: round(float(valuations.get(o, 0.0)), 6) for o in valuations}}


register_method("maximin", "decision", maximin)
register_method("maximax", "decision", maximax)
register_method("hurwicz", "decision", hurwicz)
register_method("minimax_regret", "decision", minimax_regret)
register_method("expected_utility", "decision", expected_utility)
register_method("bayesian_update", "decision", bayesian_update)
register_method("pareto", "decision", pareto)
register_method("lexicographic", "decision", lexicographic)
register_method("satisficing", "decision", satisficing)
