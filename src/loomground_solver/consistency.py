# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Universalizability / treat-like-alike (O151).

The consistency test of formal justice: an outcome must be a *function of the
legally-relevant features only*. Two cases that share the same relevant
signature yet were decided unalike are an inconsistency — the difference in
outcome is being driven by a feature the law does not license (a naked
"irrelevant feature"), so the pair is returned for inspection.

Protected-attribute mode is the direct-discrimination specialisation of the
same engine: the control set becomes *every* feature key except the protected
ones, so any diverging pair that additionally differs in >= 1 protected
attribute is flagged as ``DISCRIMINATION`` — the outcome flipped on nothing but
a protected characteristic.

The op's primary input is a small local :class:`DecidedCase` record because
:class:`~loomground_solver.case.CaseRecord` has no clean feature-map slot.
``CaseRecord`` is nonetheless *consumed* here — :func:`terminal_state` reads a
disposition string out of its ``resolution`` dict, and
:func:`decided_case_from_record` lifts a record into a ``DecidedCase`` — so the
record type is sourced, never forked. Pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .case import CaseRecord

# ── kinds of divergence ──────────────────────────────────────────────────────
IRRELEVANT = "irrelevant-feature"        # like cases (on the relevant keys) decided unalike
DISCRIMINATION = "direct-discrimination"  # cases differing only in a protected attribute decided unalike

# sentinel for "this feature key is absent" — distinct from any real value, so a
# case that omits a controlled key never counts as agreeing with one that sets it.
_ABSENT = object()


@dataclass
class DecidedCase:
    """A decided case: its feature-map and the disposition it received."""

    id: str
    features: Mapping[str, Any]   # the decided case's feature-map
    outcome: str                  # its terminal state / disposition


@dataclass(frozen=True)
class InconsistentPair:
    """An unordered pair of like cases decided unalike."""

    left: str
    right: str
    left_outcome: str
    right_outcome: str
    differing_keys: tuple         # feature keys on which the pair differs (all outside the control set)
    kind: str                     # IRRELEVANT | DISCRIMINATION

    def to_dict(self) -> dict:
        return {"left": self.left, "right": self.right,
                "left_outcome": self.left_outcome,
                "right_outcome": self.right_outcome,
                "differing_keys": list(self.differing_keys),
                "kind": self.kind}


@dataclass(frozen=True)
class ConsistencyReport:
    """The verdict: consistent, plus the offending pairs (order-stable)."""

    consistent: bool
    pairs: tuple                  # tuple[InconsistentPair], order-stable by (left, right)

    def to_dict(self) -> dict:
        return {"consistent": self.consistent,
                "pairs": [p.to_dict() for p in self.pairs]}


def _get(features: Mapping[str, Any], key: str) -> Any:
    """Read a feature, mapping a missing key to the distinct ``_ABSENT`` value."""
    return features[key] if key in features else _ABSENT


def _diverging_pairs(
    cases: Sequence[DecidedCase],
    control_keys: Iterable[str],
    kind: str,
) -> tuple:
    """Every unordered pair that AGREES on all ``control_keys`` yet was decided
    unalike, as an ``InconsistentPair`` carrying the keys they still differ on.

    A missing controlled key is treated as a distinct absent value, so two cases
    only agree on a key when both set it to the same value (or both omit it).
    """
    controls = tuple(control_keys)
    pairs: list[InconsistentPair] = []
    for i in range(len(cases)):
        for j in range(i + 1, len(cases)):
            a, b = cases[i], cases[j]
            if any(_get(a.features, k) != _get(b.features, k) for k in controls):
                continue  # not "like" cases on the control set
            if a.outcome == b.outcome:
                continue  # like cases, decided alike — consistent
            # like on the controls, yet decided unalike: report every key
            # (inside or outside the control set) on which they still differ.
            keys = sorted(set(a.features) | set(b.features))
            differing = tuple(k for k in keys
                              if _get(a.features, k) != _get(b.features, k))
            # order-stabilise the pair endpoints by id
            left, right = (a, b) if a.id <= b.id else (b, a)
            pairs.append(InconsistentPair(
                left=left.id, right=right.id,
                left_outcome=left.outcome, right_outcome=right.outcome,
                differing_keys=differing, kind=kind))
    pairs.sort(key=lambda p: (p.left, p.right))
    return tuple(pairs)


def check_consistency(
    cases: Sequence[DecidedCase],
    relevant_keys: Iterable[str],
) -> ConsistencyReport:
    """Outcome must be a function of ``relevant_keys`` only.

    Cases with the same relevant signature but a different outcome are
    inconsistent (``IRRELEVANT``): the outcome is tracking something the law
    does not license.
    """
    pairs = _diverging_pairs(cases, relevant_keys, IRRELEVANT)
    return ConsistencyReport(consistent=not pairs, pairs=pairs)


def check_nondiscrimination(
    cases: Sequence[DecidedCase],
    protected_keys: Iterable[str],
) -> ConsistencyReport:
    """Direct-discrimination test.

    The control set is *all* feature keys except the protected ones, so a
    diverging pair is one that agrees on every legitimate feature. Such a pair
    is flagged ``DISCRIMINATION`` only when it *additionally* differs in >= 1
    protected key — i.e. the outcome flipped on nothing but a protected
    attribute. A pair that also differs in a legitimate feature never enters the
    diverging set (they are not "like" cases), so it is not flagged.
    """
    protected = set(protected_keys)
    all_keys: set = set()
    for c in cases:
        all_keys |= set(c.features)
    control_keys = all_keys - protected
    diverging = _diverging_pairs(cases, control_keys, DISCRIMINATION)
    # keep only pairs that differ in at least one protected key
    pairs = tuple(p for p in diverging
                  if any(k in protected for k in p.differing_keys))
    return ConsistencyReport(consistent=not pairs, pairs=pairs)


def terminal_state(record: CaseRecord) -> str:
    """The disposition string of a decided :class:`CaseRecord`.

    ``determinate`` -> its ``answer``; ``residual`` with a recorded ``choice``
    -> the chosen label; anything else (open decision surface) -> ``'open'``.
    """
    resolution = record.resolution or {}
    if resolution.get("type") == "determinate":
        return str(resolution.get("answer", ""))
    if resolution.get("type") == "residual":
        choice = resolution.get("choice")
        if choice:
            return str(choice.get("chosen_label", "open"))
    return "open"


def decided_case_from_record(
    case_id: str,
    features: Mapping[str, Any],
    record: CaseRecord,
) -> DecidedCase:
    """Lift a :class:`CaseRecord` into a :class:`DecidedCase`, sourcing the
    outcome from the record's terminal state (``CaseRecord`` consumed, not
    forked)."""
    return DecidedCase(id=case_id, features=dict(features),
                       outcome=terminal_state(record))
