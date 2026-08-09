# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Distributive instrumentation (O149 + O150) — COMPUTE ONLY, never adjudicates.

This module answers *what each distributive principle prescribes*, and *whether an
allocation is efficient / fair* — it never declares a principle correct or an
allocation "just".

* **O149 — allocation efficiency + fair division.**
  :func:`pareto_allocations` returns the Pareto frontier of candidate allocations
  (an allocation not dominated on every agent's utility). :func:`fair_division`
  runs the two classic fairness checks over a self/other valuation matrix:
  *envy-freeness* (no agent values another's bundle above its own) and
  *proportionality* (each agent gets at least a ``1/n`` share of its own total
  valuation).

* **O150 — welfare-function evaluation.** :func:`evaluate` takes per-agent utility
  vectors for each option and, for every named welfare principle, reports which
  option that principle prescribes plus the supporting score: **utilitarian**
  (sum), **Rawlsian leximin** (maximise the floor, then the next-worst, …),
  **prioritarian** (sum of a concave transform) and **egalitarian** (the most
  equal profile, by lowest Gini).

Everything rides on symbols the package already ships and **nothing is
re-implemented**:

* :func:`loomground_solver.methods.decide.expected_utility` — a probability-1
  weighting turns Σ P(state)·u into a plain sum (utilitarian, and — over a
  concave-transformed matrix — prioritarian);
* :func:`loomground_solver.methods.decide.maximin` — the Rawlsian floor score;
* :func:`loomground_solver.methods.decide.lexicographic` — over ascending-sorted
  utility vectors this *is* leximin (the Rawlsian prescription);
* :func:`loomground_solver.methods.decide.pareto` — the allocation frontier;
* :func:`loomground_solver.distribution.inequality` — the Gini used for the
  egalitarian prescription (O148, consumed not forked).

BOUNDARY (by construction): :func:`evaluate` reports a prescription *per
principle* and never a winner across principles; nothing here emits a "correct" /
"best-principle" key. Pure stdlib, deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

from .distribution import inequality
from .methods.decide import expected_utility, lexicographic, maximin, pareto

# ── welfare principle names ───────────────────────────────────────────────────
UTILITARIAN = "utilitarian"     # Σ u_i
RAWLSIAN = "rawlsian"           # leximin: max the floor, then the next-worst, …
PRIORITARIAN = "prioritarian"   # Σ f(u_i), f concave
EGALITARIAN = "egalitarian"     # most equal profile (lowest Gini)

WELFARE_PRINCIPLES: tuple = (UTILITARIAN, RAWLSIAN, PRIORITARIAN, EGALITARIAN)


def _default_transform(u: float) -> float:
    """Default concave transform for the prioritarian sum: ``sqrt`` on the
    non-negative part. Concave and increasing, so equal spreading is favoured;
    negative utilities are clamped to ``0`` (supply your own ``transform`` for a
    signed domain)."""
    return math.sqrt(u) if u > 0.0 else 0.0


# ── O150: welfare-function evaluation ─────────────────────────────────────────
@dataclass(frozen=True)
class WelfareEvaluation:
    """What each welfare principle prescribes over the option set — no winner.

    ``prescriptions``/``rankings``/``scores`` are keyed by principle name; there
    is deliberately no cross-principle "correct" verdict.
    """

    options: tuple                       # option ids, in input order
    prescriptions: dict                  # principle -> chosen option (or None)
    rankings: dict                       # principle -> [option, …] best-first
    scores: dict                         # principle -> {option: score}
    metrics: dict                        # {option: {"total","floor","gini"}}

    def to_dict(self) -> dict:
        return {
            "options": list(self.options),
            "prescriptions": dict(self.prescriptions),
            "rankings": {k: list(v) for k, v in self.rankings.items()},
            "scores": {k: dict(v) for k, v in self.scores.items()},
            "metrics": {o: dict(m) for o, m in self.metrics.items()},
        }


def evaluate(
    utilities: Mapping[str, Sequence[float]],
    *,
    transform: Optional[Callable[[float], float]] = None,
) -> WelfareEvaluation:
    """Evaluate every welfare principle over ``utilities``.

    ``utilities`` maps ``option -> per-agent utility vector`` (all vectors the
    same length, one entry per agent). For each principle the chosen option, the
    best-first ranking and a per-option score are reported by *wrapping* the
    existing decision/inequality engines:

    * utilitarian — :func:`decide.expected_utility` with every agent weighted
      ``1.0`` (Σ P·u collapses to Σ u);
    * Rawlsian — :func:`decide.lexicographic` over each vector sorted ascending
      (leximin) for the choice/ranking, with the floor score from
      :func:`decide.maximin`;
    * prioritarian — the utilitarian wrapper over ``transform``-mapped utilities
      (``transform`` defaults to a clamped ``sqrt``);
    * egalitarian — lowest :func:`distribution.inequality` Gini (most equal).

    Reports a prescription per principle only; never a winner across principles.
    """
    options = tuple(utilities)
    fn = transform or _default_transform

    # per-agent "state" keys are agent indices, shared across all options.
    payoffs = {o: {i: float(u) for i, u in enumerate(vec)}
               for o, vec in utilities.items()}
    prio_payoffs = {o: {i: fn(float(u)) for i, u in enumerate(vec)}
                    for o, vec in utilities.items()}
    # weight 1.0 per agent => Σ P·u is exactly Σ u (not the mean).
    weights = {i: 1.0 for o in payoffs for i in payoffs[o]}

    util = expected_utility(payoffs=payoffs, probabilities=weights)
    prio = expected_utility(payoffs=prio_payoffs, probabilities=weights)
    floor = maximin(payoffs=payoffs)
    leximin = lexicographic(
        vectors={o: tuple(sorted(float(u) for u in vec))
                 for o, vec in utilities.items()})

    ginis = {o: inequality([float(u) for u in vec]).gini
             for o, vec in utilities.items()}
    egal_ranking = sorted(options, key=lambda o: (ginis[o], o))  # lower Gini first

    prescriptions = {
        UTILITARIAN: util["choice"],
        RAWLSIAN: leximin["choice"],
        PRIORITARIAN: prio["choice"],
        EGALITARIAN: egal_ranking[0] if egal_ranking else None,
    }
    rankings = {
        UTILITARIAN: list(util["ranking"]),
        RAWLSIAN: list(leximin["ranking"]),
        PRIORITARIAN: list(prio["ranking"]),
        EGALITARIAN: egal_ranking,
    }
    scores = {
        UTILITARIAN: dict(util["scores"]),
        RAWLSIAN: dict(floor["scores"]),            # the Rawlsian floor per option
        PRIORITARIAN: dict(prio["scores"]),
        EGALITARIAN: {o: ginis[o] for o in options},
    }
    metrics = {
        o: {"total": util["scores"].get(o, 0.0),
            "floor": floor["scores"].get(o, 0.0),
            "gini": ginis[o]}
        for o in options
    }
    return WelfareEvaluation(options=options, prescriptions=prescriptions,
                             rankings=rankings, scores=scores, metrics=metrics)


# ── O149a: allocation Pareto-efficiency ───────────────────────────────────────
@dataclass(frozen=True)
class ParetoReport:
    """The Pareto frontier over candidate allocations — efficiency, not a verdict."""

    frontier: tuple                      # allocation ids on the frontier (sorted)
    dominated: tuple                     # allocation ids dominated by some other (sorted)
    on_frontier: dict                    # allocation id -> bool

    def to_dict(self) -> dict:
        return {"frontier": list(self.frontier),
                "dominated": list(self.dominated),
                "on_frontier": dict(self.on_frontier)}


def pareto_allocations(
    allocations: Mapping[str, Sequence[float]],
) -> ParetoReport:
    """Pareto frontier over ``allocations`` (``id -> per-agent utility vector``).

    Wraps :func:`decide.pareto`: an allocation is on the frontier iff no other
    allocation is at least as good for every agent and strictly better for one.
    Higher utility is better on each agent's axis. Efficiency only — never a claim
    that a frontier allocation is the "right" one.
    """
    result = pareto(vectors={a: list(vec) for a, vec in allocations.items()})
    scores = result["scores"]
    frontier = tuple(sorted(a for a in allocations if scores.get(a, 0.0) == 1.0))
    dominated = tuple(sorted(a for a in allocations if scores.get(a, 0.0) != 1.0))
    on_frontier = {a: (scores.get(a, 0.0) == 1.0) for a in allocations}
    return ParetoReport(frontier=frontier, dominated=dominated,
                        on_frontier=on_frontier)


# ── O149b: fair division (envy-freeness + proportionality) ────────────────────
@dataclass(frozen=True)
class FairDivisionReport:
    """Envy-freeness + proportionality over a self/other valuation matrix.

    A fairness *measurement*: which agents envy, which fall short of a
    proportional share. Never a verdict that the division is "fair" / "unfair".
    """

    envy_free: bool                      # no agent envies another's bundle
    proportional: bool                   # every agent clears its 1/n share
    envious_agents: tuple                # agents whose own bundle is not their most-valued
    envy_pairs: tuple                    # (i, j): i values j's bundle above its own
    under_proportional: tuple            # agents below the 1/n threshold
    shares: dict                         # agent -> {"own","threshold"} (own value vs 1/n share)

    def to_dict(self) -> dict:
        return {"envy_free": self.envy_free,
                "proportional": self.proportional,
                "envious_agents": list(self.envious_agents),
                "envy_pairs": [list(p) for p in self.envy_pairs],
                "under_proportional": list(self.under_proportional),
                "shares": {a: dict(s) for a, s in self.shares.items()}}


def fair_division(
    valuations: Mapping[str, Mapping[str, float]],
) -> FairDivisionReport:
    """Fair-division checks over a valuation matrix.

    ``valuations[i][j]`` is agent ``i``'s value for the bundle assigned to agent
    ``j`` (so ``valuations[i][i]`` is ``i``'s value for its OWN bundle). Over the
    ``n`` agents:

    * **envy-free** iff no agent values another agent's bundle strictly above its
      own — each ``valuations[i][j]`` reported when it exceeds ``valuations[i][i]``;
    * **proportional** iff every agent's own value clears ``(Σ_j valuations[i][j]) / n``.

    Pure measurement — flags who envies and who falls short; never a verdict.
    """
    agents = list(valuations)
    n = len(agents)

    envy_pairs: list[tuple] = []
    envious: list[str] = []
    under: list[str] = []
    shares: dict = {}

    for i in agents:
        row = valuations[i]
        own = float(row.get(i, 0.0))
        # envy: any other agent's bundle valued strictly above own
        envied_here = [j for j in agents
                       if j != i and float(row.get(j, 0.0)) > own]
        for j in envied_here:
            envy_pairs.append((i, j))
        if envied_here:
            envious.append(i)
        # proportionality: own value vs a 1/n share of the total valuation
        total = sum(float(row.get(j, 0.0)) for j in agents)
        threshold = total / n if n else 0.0
        shares[i] = {"own": own, "threshold": threshold}
        if own < threshold:
            under.append(i)

    return FairDivisionReport(
        envy_free=not envy_pairs,
        proportional=not under,
        envious_agents=tuple(envious),
        envy_pairs=tuple(envy_pairs),
        under_proportional=tuple(under),
        shares=shares,
    )
