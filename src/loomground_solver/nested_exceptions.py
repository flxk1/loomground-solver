# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Nested exceptions — Ausnahme / Rückausnahme trees (O58).

Real legal rules are rarely ``rule minus one exception``. A rule carries an
*exception* (Ausnahme); the exception may itself carry a *counter-exception*
(Rückausnahme) that defeats it; and a counter-exception may in turn be defeated,
to arbitrary depth. The polarity alternates with depth: an odd level of firing
blocks the rule, an even level restores it.

This module walks such a tree and reports, for a set of facts, whether the rule
is **blocked** — together with the decisive branch, so the reasoning can be
audited (which node fired, which counter-exception defeated it, how deep the
tree had to be read).

The per-node truth check is **consumed**, not reimplemented: every condition is
decided by :func:`loomground_solver.subsumption.holds` under the same
closed-world default (unproven ≠ true) with the same optional ``judge`` model
escalation. A node fires iff its condition holds *and none of its children fire*
— recursion is the whole mechanism.

Pure stdlib. No governance, no domain."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from .subsumption import holds


@dataclass(frozen=True)
class ExceptionNode:
    """One node of an exception tree.

    ``condition`` is a literal (the same vocabulary :func:`subsumption.holds`
    reads). ``children`` are the counter-exceptions (Rückausnahmen) that, when
    they fire, defeat *this* node. ``label`` is an optional human name used in
    the firing chain; it falls back to ``condition`` when empty.
    """

    condition: str
    children: tuple = ()          # tuple[ExceptionNode] — the Rückausnahmen
    label: str = ""


def _label_of(node: ExceptionNode) -> str:
    """The name used in a firing chain: the explicit label, else the condition."""
    return node.label or node.condition


@dataclass
class NodeEval:
    """The evaluation of a single :class:`ExceptionNode` against the facts."""

    node: ExceptionNode
    level: int                    # 1 for a top-level exception, +1 per nesting
    condition_holds: bool         # did subsumption.holds decide the condition true?
    fired: bool                   # condition holds AND no child fired
    decisive_level: int           # deepest level consulted on this node's branch
    defeated_by: tuple            # labels of the children that fired (defeated it)
    children: tuple               # tuple[NodeEval]


@dataclass
class ExceptionVerdict:
    """The rule-level verdict over a whole forest of top-level exceptions."""

    blocked: bool                 # did any top-level exception fire?
    deciding_level: int           # deepest level consulted on the decisive branch
    firing_chain: tuple           # labels that FIRED along the decisive branch, top→deep
    evaluations: tuple            # tuple[NodeEval] — the top-level nodes, fully expanded


def _decisive_child(children: Sequence[NodeEval]) -> Optional[NodeEval]:
    """The child that determines this node's fate / depth.

    A firing child defeats the parent, so it is decisive (first one on ties).
    Otherwise the branch that was read deepest is the decisive one — that is the
    node that had to be consulted to conclude no counter-exception fired.
    """
    fired = [c for c in children if c.fired]
    if fired:
        return fired[0]
    if children:
        return max(children, key=lambda c: c.decisive_level)
    return None


def _eval_node(node: ExceptionNode, level: int, facts: set,
               judge: Optional[Callable[[str, set], bool]]) -> NodeEval:
    """Recursively evaluate ``node``: it fires iff its condition holds (per
    :func:`subsumption.holds`) and none of its children fire."""
    cond = holds(node.condition, facts, judge=judge)
    child_evals = tuple(
        _eval_node(c, level + 1, facts, judge) for c in node.children
    )
    fired_children = tuple(c for c in child_evals if c.fired)
    fired = cond and not fired_children
    decisive = _decisive_child(child_evals)
    decisive_level = decisive.decisive_level if decisive is not None else level
    defeated_by = tuple(_label_of(c.node) for c in fired_children)
    return NodeEval(
        node=node,
        level=level,
        condition_holds=cond,
        fired=fired,
        decisive_level=decisive_level,
        defeated_by=defeated_by,
        children=child_evals,
    )


def _firing_chain(ev: NodeEval) -> tuple:
    """Labels that fired along ``ev``'s decisive branch, top→deep."""
    head: tuple = (_label_of(ev.node),) if ev.fired else ()
    decisive = _decisive_child(ev.children)
    tail = _firing_chain(decisive) if decisive is not None else ()
    return head + tail


def evaluate_exceptions(exceptions: Sequence[ExceptionNode], facts: set, *,
                        judge: Optional[Callable[[str, set], bool]] = None
                        ) -> ExceptionVerdict:
    """Evaluate an exception forest against ``facts`` and report the verdict.

    The rule is **blocked** iff any top-level exception fires. A node fires iff
    :func:`subsumption.holds` decides its condition true *and* none of its
    children (Rückausnahmen) fire — so a firing counter-exception un-blocks the
    rule, a firing counter-counter-exception re-blocks it, and so on.

    ``deciding_level`` is the deepest level consulted on the decisive branch (0
    when there are no exceptions); ``firing_chain`` is the tuple of labels of the
    nodes that fired along that branch, ordered top→deep. ``judge`` is threaded
    through to :func:`subsumption.holds` only.
    """
    evals = tuple(_eval_node(e, 1, set(facts), judge) for e in exceptions)
    fired_top = [e for e in evals if e.fired]
    blocked = bool(fired_top)
    if not evals:
        return ExceptionVerdict(False, 0, (), ())
    # the decisive top-level branch: a firing exception (it blocks), else the
    # branch read deepest (it explains why nothing blocked).
    decisive_top = fired_top[0] if fired_top else max(
        evals, key=lambda e: e.decisive_level
    )
    return ExceptionVerdict(
        blocked=blocked,
        deciding_level=decisive_top.decisive_level,
        firing_chain=_firing_chain(decisive_top),
        evaluations=evals,
    )


def blocks(exceptions: Sequence[ExceptionNode], facts: set, *,
           judge: Optional[Callable[[str, set], bool]] = None) -> bool:
    """Convenience: ``True`` iff the exception forest blocks the rule."""
    return evaluate_exceptions(exceptions, facts, judge=judge).blocked
