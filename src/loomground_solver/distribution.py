# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Distribution measurement (Family T, O148 + O152) — MEASURE ONLY.

Two instruments live here, and both stop at the numbers.

* **O148 — inequality over a distribution of holdings** (:func:`inequality`):
  pure arithmetic over a sequence of non-negative holdings. Reports the Gini
  coefficient, the range, the max/min ratio and the raw totals. It reports how
  unequal a distribution *is*; it never labels a distribution "unequal" or
  "unjust".

* **O152 — indirect-discrimination disparity** (:func:`adverse_impact`): the
  four-fifths / adverse-impact rule. Given favourable-outcome rates per group it
  computes each group's ratio to the highest-rate (reference) group and *flags*
  the groups whose ratio falls below the 80% line. A breach is a **flag for
  escalation, not a finding of discrimination** — the verdict of
  "discriminatory" / "unlawful" is deliberately outside this module.

:func:`rates_from_cases` is the bridge from decided cases into the O152 input: it
buckets :class:`~loomground_solver.consistency.DecidedCase` records by a feature
key and counts favourable outcomes, so the grouped-outcome record is *sourced*
from ``consistency`` and never forked here. Pure stdlib, deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence, Union

from .consistency import DecidedCase

# The 80% adverse-impact threshold — a *detection line*, not a verdict. A ratio
# below this is flagged for escalation; the flag is not itself a finding.
FOUR_FIFTHS: float = 0.8


# ── O148: inequality over a distribution of holdings — pure arithmetic ────────
@dataclass(frozen=True)
class InequalityMetrics:
    """Inequality metrics over a distribution of holdings — numbers only."""

    gini: float            # Gini coefficient in [0,1]; 0 for empty/single/all-equal
    range: float           # max - min
    ratio: float           # max / min (inf when min==0 and max>0; 1.0 when all zero)
    minimum: float
    maximum: float
    total: float
    n: int

    def to_dict(self) -> dict:
        return {"gini": self.gini, "range": self.range, "ratio": self.ratio,
                "minimum": self.minimum, "maximum": self.maximum,
                "total": self.total, "n": self.n}


def inequality(holdings: Sequence[float]) -> InequalityMetrics:
    """Inequality metrics over ``holdings`` (assumed non-negative).

    The Gini coefficient is computed via the sorted cumulative form
    ``G = (2 * Σ i*x_i) / (n * Σx) - (n + 1) / n`` with the values sorted
    ascending and ``i`` 1-based. An empty, single-element or all-equal
    distribution has a vacuous Gini of ``0.0``; when ``Σx == 0`` the guard also
    returns ``0.0``. Reports metrics only — no "unequal" / "unjust" label.
    """
    values = [float(x) for x in holdings]
    n = len(values)
    if n == 0:
        return InequalityMetrics(gini=0.0, range=0.0, ratio=1.0,
                                 minimum=0.0, maximum=0.0, total=0.0, n=0)

    ordered = sorted(values)
    minimum = ordered[0]
    maximum = ordered[-1]
    total = sum(ordered)
    range_ = maximum - minimum

    if minimum == 0.0:
        ratio = 1.0 if maximum == 0.0 else float("inf")
    else:
        ratio = maximum / minimum

    if total == 0.0:
        gini = 0.0
    else:
        weighted = sum((i + 1) * x for i, x in enumerate(ordered))  # i 1-based
        gini = (2.0 * weighted) / (n * total) - (n + 1) / n

    return InequalityMetrics(gini=gini, range=range_, ratio=ratio,
                             minimum=minimum, maximum=maximum,
                             total=total, n=n)


# ── O152: indirect-discrimination disparity (four-fifths / adverse-impact) ────
@dataclass(frozen=True)
class ImpactRatio:
    """Four-fifths / adverse-impact metrics — rates, ratio and flags only.

    A ``breaches`` of ``True`` (or a non-empty ``flagged_pairs``) is a signal for
    escalation, NOT a finding of discrimination.
    """

    rates: dict                 # group -> favourable-outcome rate
    reference_group: str        # group with the highest rate (the benchmark)
    reference_rate: float
    disadvantaged_group: str    # group with the lowest rate
    lowest_rate: float
    ratio: float                # lowest_rate / reference_rate; 1.0 if reference_rate==0
    threshold: float            # == FOUR_FIFTHS unless overridden
    breaches: bool              # ratio < threshold — a FLAG for escalation
    flagged_pairs: tuple        # tuple[(group, ratio_vs_reference)] below threshold

    def to_dict(self) -> dict:
        return {"rates": dict(self.rates),
                "reference_group": self.reference_group,
                "reference_rate": self.reference_rate,
                "disadvantaged_group": self.disadvantaged_group,
                "lowest_rate": self.lowest_rate,
                "ratio": self.ratio,
                "threshold": self.threshold,
                "breaches": self.breaches,
                "flagged_pairs": [list(pair) for pair in self.flagged_pairs]}


def adverse_impact(
    outcomes: Mapping[str, tuple],
    *,
    threshold: float = FOUR_FIFTHS,
) -> ImpactRatio:
    """Four-fifths rule over per-group ``(favourable_count, total_count)`` pairs.

    ``outcomes`` maps ``group -> (favourable_count, total_count)``; each rate is
    ``favourable_count / total_count`` and groups with ``total_count == 0`` are
    skipped. Each group's ratio is taken against the highest-rate (reference)
    group, and any group whose ratio falls below ``threshold`` is collected in
    ``flagged_pairs``. Returns metrics + flags ONLY — never a verdict of
    "discriminatory" / "unlawful"; that is left to escalation.
    """
    rates: dict = {}
    for group, counts in outcomes.items():
        favourable_count, total_count = counts
        if total_count == 0:
            continue  # no denominator — group carries no rate
        rates[group] = favourable_count / total_count

    if not rates:
        return ImpactRatio(rates={}, reference_group="", reference_rate=0.0,
                           disadvantaged_group="", lowest_rate=0.0, ratio=1.0,
                           threshold=threshold, breaches=False,
                           flagged_pairs=())

    reference_group = max(rates, key=lambda g: rates[g])
    reference_rate = rates[reference_group]
    disadvantaged_group = min(rates, key=lambda g: rates[g])
    lowest_rate = rates[disadvantaged_group]

    if reference_rate == 0.0:
        # every group has a zero rate — no disparity to measure.
        ratio = 1.0
        flagged_pairs: tuple = ()
    else:
        ratio = lowest_rate / reference_rate
        flagged_pairs = tuple(
            (group, rates[group] / reference_rate)
            for group in rates
            if rates[group] / reference_rate < threshold
        )

    return ImpactRatio(rates=rates, reference_group=reference_group,
                       reference_rate=reference_rate,
                       disadvantaged_group=disadvantaged_group,
                       lowest_rate=lowest_rate, ratio=ratio,
                       threshold=threshold, breaches=ratio < threshold,
                       flagged_pairs=flagged_pairs)


def rates_from_cases(
    cases: Sequence[DecidedCase],
    *,
    group_key: str,
    favourable: Union[set, Callable[[str], bool]],
) -> dict:
    """Bucket ``cases`` by ``features[group_key]`` and count favourable outcomes.

    ``favourable`` is either a set of outcome strings or a predicate
    ``str -> bool``. Cases lacking ``group_key`` are skipped. Returns
    ``group -> (favourable_count, total_count)``, feedable straight into
    :func:`adverse_impact`. Consumes :class:`DecidedCase` — sourced, not forked.
    """
    is_favourable: Callable[[str], bool]
    if callable(favourable):
        is_favourable = favourable
    else:
        favourable_set = set(favourable)
        is_favourable = lambda outcome: outcome in favourable_set  # noqa: E731

    counts: dict = {}
    for case in cases:
        if group_key not in case.features:
            continue
        group = case.features[group_key]
        favourable_count, total_count = counts.get(group, (0, 0))
        total_count += 1
        if is_favourable(case.outcome):
            favourable_count += 1
        counts[group] = (favourable_count, total_count)
    return counts
