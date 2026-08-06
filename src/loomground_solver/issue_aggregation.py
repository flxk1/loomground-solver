# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Issue aggregation — fold already-decided sub-issue verdicts up the issue
structure, honestly.

:mod:`cross_subsumption` decides one condition (and a whole antecedent) across
the five reasoning dimensions. A legal *issue* — a claim's life, a defence's
elements — is usually not a single antecedent but a small tree of sub-issues:
"the claim exists AND has not perished AND is enforceable". Each sub-issue is
*already* a :class:`cross_subsumption.Verdict` (SATISFIED / NOT_SATISFIED /
OPEN), produced upstream. This op does **one** thing and does not redo any of
it: it **aggregates** those sub-issue verdicts into one overall verdict on the
issue.

It is deterministic [D]: fixed sub-issue verdicts fold to a fixed overall
verdict. There is no model, no ``ModelFn``, no stub — it never *decides* a
sub-issue, only *combines* decisions handed to it. It **consumes**
:class:`cross_subsumption.Verdict` (and coerces the ``AntecedentVerdict`` /
``DimVerdict`` wrappers via their ``.verdict``) rather than redefining the
verdict vocabulary. It imports neither ``loomground_legal`` nor
``loomground_versum``.

Two folds, both escalation-dominant and honest:

  * **default (unordered)** — strict AND across the sub-issues: **any** OPEN
    sub-issue makes the whole issue **OPEN** (escalate), *dominating* even a
    NOT_SATISFIED sibling — an issue resting on an unresolved element is neither
    met nor unmet, it is open. Else all SATISFIED → **SATISFIED**
    (determinate). Else (some NOT_SATISFIED, none OPEN) → **NOT_SATISFIED**.
    The empty issue is **vacuously SATISFIED**. OPEN is never fabricated into
    SATISFIED, and an OPEN sibling is never collapsed to NOT_SATISFIED.

  * **ordered (``order=``, an Aufbau)** — the sub-issues have a dependency
    order: a later sub-issue is only *reached* if every earlier one is
    SATISFIED. Walk them in ``order``; the first non-SATISFIED sub-issue decides
    the overall verdict (OPEN or NOT_SATISFIED) and stops the walk. Only the
    reached prefix is carried on the result — the unreached tail was never
    evaluated and is not reported as if it were. This models constructive
    ("Aufbau") reasoning where you never reach the deadline question until the
    claim is shown to exist.

Pure stdlib. No new dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple, Union

from .cross_subsumption import AntecedentVerdict, DimVerdict, Verdict, fold_verdicts

#: A sub-issue verdict may arrive as a bare :class:`Verdict` or wrapped in an
#: :class:`AntecedentVerdict` / :class:`DimVerdict` (both expose ``.verdict``).
VerdictLike = Union[Verdict, AntecedentVerdict, DimVerdict]


# ── output ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IssueAggregate:
    """The overall verdict on an issue, carrying every reached sub-issue verdict.

    ``issues`` is the ordered tuple of ``(name, Verdict)`` that actually decided
    the outcome: the full set in the default fold, or the reached prefix under an
    ``order=`` Aufbau. ``reason`` explains which sub-issue drove the result.
    """

    overall: Verdict
    issues: Tuple[Tuple[str, Verdict], ...]
    reason: str = ""

    @property
    def satisfied(self) -> bool:
        return self.overall is Verdict.SATISFIED

    @property
    def open(self) -> bool:
        return self.overall is Verdict.OPEN


# ── coercion ───────────────────────────────────────────────────────────────────

def _as_verdict(v: VerdictLike) -> Verdict:
    """Coerce a sub-issue verdict to a bare :class:`Verdict`.

    Accepts a :class:`Verdict` directly, or any wrapper exposing a ``.verdict``
    that is itself a :class:`Verdict` (an :class:`AntecedentVerdict` or
    :class:`DimVerdict`). Anything else — a raw string, ``None``, an int — is a
    type error, never silently coerced. This op consumes the verdict vocabulary;
    it never redefines or guesses it.
    """
    if isinstance(v, Verdict):
        return v
    inner = getattr(v, "verdict", None)
    if isinstance(inner, Verdict):
        return inner
    raise TypeError(
        f"sub-issue verdict must be a Verdict or a wrapper exposing a "
        f"Verdict `.verdict` (AntecedentVerdict/DimVerdict), got {type(v).__name__}"
    )


# ── the op ─────────────────────────────────────────────────────────────────────

def aggregate_issues(
    issues: Iterable[Tuple[str, VerdictLike]],
    *,
    order: Optional[Sequence[str]] = None,
) -> IssueAggregate:
    """Fold sub-issue verdicts into one overall issue verdict.

    ``issues`` is an iterable of ``(name, verdict)`` where ``verdict`` is a
    :class:`cross_subsumption.Verdict` or a wrapper exposing one (coerced via
    :func:`_as_verdict`).

    Without ``order`` — the **default unordered strict-AND fold**, escalation
    dominant:

      * **any** OPEN sub-issue → overall **OPEN** (dominates even a
        NOT_SATISFIED sibling);
      * else all SATISFIED → overall **SATISFIED**;
      * else (some NOT_SATISFIED, none OPEN) → overall **NOT_SATISFIED**;
      * empty → **vacuously SATISFIED**.

    Every sub-issue verdict is carried on ``result.issues``.

    With ``order`` — a short-circuiting **Aufbau**: sub-issues are walked in the
    given dependency order, and a later one is reached only if every earlier one
    is SATISFIED. The first non-SATISFIED sub-issue decides the overall verdict
    (OPEN or NOT_SATISFIED) and stops the walk; only the reached prefix is
    carried. ``order=[]`` reaches nothing and is vacuously SATISFIED. A name in
    ``order`` not present in ``issues`` is skipped; sub-issues absent from
    ``order`` are simply never reached.
    """
    resolved = tuple((name, _as_verdict(v)) for name, v in issues)

    if order is None:
        return _fold_unordered(resolved)
    return _fold_ordered(resolved, order)


def _fold_unordered(
    resolved: Tuple[Tuple[str, Verdict], ...],
) -> IssueAggregate:
    overall = fold_verdicts(v for _, v in resolved)   # the one canonical OPEN-dominant fold
    if overall is Verdict.OPEN:
        opens = [n for n, v in resolved if v is Verdict.OPEN]
        return IssueAggregate(
            overall, resolved,
            reason=f"{len(opens)} sub-issue(s) OPEN → issue OPEN (escalate, "
                   f"dominating any NOT_SATISFIED sibling): " + "; ".join(opens))
    if overall is Verdict.NOT_SATISFIED:
        unmet = [n for n, v in resolved if v is Verdict.NOT_SATISFIED]
        return IssueAggregate(
            overall, resolved,
            reason=f"{len(unmet)} sub-issue(s) NOT_SATISFIED, none OPEN → issue "
                   f"NOT_SATISFIED: " + "; ".join(unmet))
    if not resolved:
        return IssueAggregate(
            overall, resolved,
            reason="no sub-issues → vacuously SATISFIED")
    return IssueAggregate(
        overall, resolved,
        reason="all sub-issues SATISFIED → issue SATISFIED (determinate)")


def _fold_ordered(
    resolved: Tuple[Tuple[str, Verdict], ...],
    order: Sequence[str],
) -> IssueAggregate:
    by_name = dict(resolved)
    reached: list[Tuple[str, Verdict]] = []
    for name in order:
        if name not in by_name:
            continue
        v = by_name[name]
        reached.append((name, v))
        if v is Verdict.SATISFIED:
            continue
        # First non-SATISFIED sub-issue decides and stops the Aufbau.
        carried = tuple(reached)
        if v is Verdict.OPEN:
            return IssueAggregate(
                Verdict.OPEN, carried,
                reason=f"Aufbau reached {name!r} = OPEN → issue OPEN (escalate); "
                       f"later sub-issues never reached")
        return IssueAggregate(
            Verdict.NOT_SATISFIED, carried,
            reason=f"Aufbau reached {name!r} = NOT_SATISFIED → issue "
                   f"NOT_SATISFIED; later sub-issues never reached")
    carried = tuple(reached)
    if not carried:
        return IssueAggregate(
            Verdict.SATISFIED, carried,
            reason="Aufbau reached no sub-issues → vacuously SATISFIED")
    return IssueAggregate(
        Verdict.SATISFIED, carried,
        reason="Aufbau: every reached sub-issue SATISFIED → issue SATISFIED")
