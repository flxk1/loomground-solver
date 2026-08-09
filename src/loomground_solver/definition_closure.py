# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Definitional closure — transitively expand a defined term through INJECTED
definitional edges, detect definitional cycles, and yield the closed definition
for substitution into subsumption.

A legal (or any) term is rarely primitive: "personal data" is defined as an
"identifier", which is defined as an "attribute", … A rule condition that names
the term can only be decided once the term is *expanded* to the tokens it
ultimately stands for. This op performs that expansion — the **definitional
closure** — over definitional edges that arrive as **data** (``term
→[defining relation]→ defining token``), never by importing a corpus. The solver
stays corpus-free: this module imports neither ``loomground_legal`` nor
``loomground_versum``.

Consume-don't-regrow. The transitive reach is **not** hand-rolled: it is
:func:`reasoning.compose_paths` (``start=<term>``, ``min_hops=1``) — the bounded,
deterministic, acyclic path enumeration over :class:`reasoning.Edge`, with full
per-path provenance. Relation-type coherence along each reached chain is
**not** hand-rolled either: it is :meth:`relation.RelationAlgebra.compose_path`,
whose :data:`relation.ESCALATE` / escalated flag / ``None`` composite marks a
branch *contested* and demotes it to OPEN instead of admitting it into the
settled expansion.

The one thing neither of those reports is a **definitional cycle**: both
existing closures avoid loops by *silent pruning* (dropping the back-edge with no
signal), so a term that is defined (directly or transitively) in terms of itself
would vanish invisibly. Cycle *detection* is therefore the only piece added here,
additively — a small white/gray/black back-edge DFS (the proven algorithm of
``loomground._has_cycle``, but returning the offending term ring rather than a
bare bool, and without coupling a clean op to the governance module). A
definitional cycle is surfaced as a first-class result (``open=True`` +
``cycle=<ring>``, mirroring :class:`cross_subsumption.Verdict.OPEN` and
:mod:`closure`), never looped on.

Honesty, throughout:

  * an **undefined** term (no definitional edge names it) yields an explicit
    empty/unknown result — ``defined=False`` — never a fabricated definition;
  * a **cycle** reachable from the term ⇒ ``open=True`` with the ring named;
  * a **contested** composition (ESCALATE / no coherent relation) demotes that
    branch to OPEN; its token is *not* admitted into the settled closure;
  * otherwise the closure is the union of the reached defining tokens.

Pure stdlib + the solver substrate. No governance, no corpus, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .dimensions import Dimension
from .reasoning import Edge, compose_paths
from .relation import ESCALATE, RelationAlgebra
from .subsumption import Judge


# ── result ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClosedDefinition:
    """The closed definition of one term over the injected definitional edges.

    ``tokens`` is the **settled** transitive closure — the union of defining
    tokens reached along coherent, acyclic definitional chains. It is what gets
    substituted into subsumption (see :meth:`as_facts` / :meth:`judge`).

    ``open`` is the escalate signal, first-class and correct: it is ``True`` when
    a definitional ``cycle`` was found reachable from the term, or when at least
    one reached branch was ``contested`` (ESCALATE / no coherent relation). An
    open closure must not be treated as fully settled.

    ``defined`` is ``False`` for a term no definitional edge names — an explicit
    unknown, never a fabricated definition (``tokens`` is then empty and ``open``
    is ``False``: unknown is not the same as contested).
    """

    term: str
    defined: bool                       # False ⇒ no definitional edge names the term
    tokens: frozenset                   # the settled transitive closure (defining tokens)
    open: bool                          # True ⇒ a cycle or a contested branch escalated
    cycle: Optional[tuple] = None       # the offending term ring, when a cycle was found
    contested: tuple = ()               # branches demoted to OPEN (dicts: object/chain/composed)
    paths: tuple = ()                   # provenance: the admitted Inference paths (as dicts)
    reason: str = ""

    # ── substitution seam into subsumption ─────────────────────────────────────
    def as_facts(self) -> frozenset:
        """The expansion as closed-world literals — inject alongside the case
        facts so a :class:`subsumption.Rule` condition naming a defining token is
        decided by the expansion."""
        return self.tokens

    def judge(self) -> Judge:
        """A :data:`subsumption.Judge` callback deciding an open literal by
        membership in the expansion, for the ``holds(..., judge=…)`` seam."""
        toks = self.tokens

        def _judge(lit: str, facts: set) -> bool:
            return lit in toks

        return _judge

    def to_dict(self) -> dict:
        return {
            "term": self.term,
            "defined": self.defined,
            "tokens": sorted(self.tokens),
            "open": self.open,
            "cycle": list(self.cycle) if self.cycle is not None else None,
            "contested": [dict(c) for c in self.contested],
            "paths": [dict(p) for p in self.paths],
            "reason": self.reason,
        }


# ── edge coercion ──────────────────────────────────────────────────────────────

def _coerce_edges(edges: Iterable[Any]) -> list[Edge]:
    """Accept the injected definitional edges as :class:`reasoning.Edge`, plain
    ``(subject, predicate, object)`` tuples, or ``{"subject","predicate",
    "object"}`` dicts. Definitional edges default to the STRUCTURAL dimension
    (is-a / defined-as / part-of). Malformed items are skipped, not raised on."""
    out: list[Edge] = []
    for e in edges or ():
        if isinstance(e, Edge):
            out.append(e)
            continue
        if isinstance(e, dict):
            subj, pred, obj = e.get("subject"), e.get("predicate"), e.get("object")
            dim = e.get("dimension", Dimension.STRUCTURAL)
            if subj and obj:
                out.append(Edge(str(subj), str(pred or ""), str(obj),
                                Dimension(dim) if dim else Dimension.STRUCTURAL))
            continue
        if isinstance(e, (tuple, list)) and len(e) >= 3:
            subj, pred, obj = e[0], e[1], e[2]
            if subj and obj:
                out.append(Edge(str(subj), str(pred or ""), str(obj),
                                Dimension.STRUCTURAL))
    return out


# ── definitional-cycle detection (the one piece added additively) ──────────────

_WHITE, _GRAY, _BLACK = 0, 1, 2
_SENTINEL = object()


def _find_definitional_cycle(
    adjacency: dict[str, list[str]], start: str
) -> Optional[tuple]:
    """Return the term ring of a definitional cycle reachable from ``start``, or
    ``None`` when the reachable definitional graph is acyclic.

    Iterative white/gray/black back-edge DFS — the proven algorithm of
    ``loomground._has_cycle``, but (a) seeded only from ``start`` (a cycle *the
    term reaches*, self-loops ``T→T`` included) and (b) reconstructing and
    returning the offending ring ``(n₀, …, nₖ, n₀)`` rather than a bare bool, so
    the honesty signal names the loop instead of merely flagging it.
    """
    color: dict[str, int] = {start: _GRAY}
    parent: dict[str, str] = {}
    stack: list[tuple[str, Any]] = [(start, iter(adjacency.get(start, ())))]
    while stack:
        node, it = stack[-1]
        nxt = next(it, _SENTINEL)
        if nxt is _SENTINEL:
            color[node] = _BLACK
            stack.pop()
            continue
        c = color.get(nxt, _WHITE)
        if c == _GRAY:
            # Back-edge node→nxt onto a node still on the DFS stack: a cycle.
            # Walk parents from node up to nxt to recover the ring, then close it.
            ring = [node]
            cur = node
            while cur != nxt:
                cur = parent[cur]
                ring.append(cur)
            ring.reverse()
            ring.append(nxt)
            return tuple(ring)
        if c == _WHITE:
            color[nxt] = _GRAY
            parent[nxt] = node
            stack.append((nxt, iter(adjacency.get(nxt, ()))))
        # BLACK: fully explored, no new cycle through it.
    return None


# ── the op ─────────────────────────────────────────────────────────────────────

def close_definition(
    term: str,
    edges: Iterable[Any],
    *,
    relations: Optional[RelationAlgebra] = None,
    max_depth: int = 64,
    max_results: int = 1000,
) -> ClosedDefinition:
    """Transitively close ``term`` over the injected definitional ``edges``.

    Steps, in order:

      1. **Cycle detection** (the added honesty signal) — a small white/gray/black
         DFS over the definitional edges reachable from ``term``. A definitional
         cycle (``term`` reachable back to itself along the definitional edges,
         self-definition ``T→T`` included) is reported as ``open=True`` with the
         offending ``cycle`` ring named. The cyclic branch is not chased into a
         loop; the acyclic reach (below) is still surfaced for provenance.

      2. **Transitive reach** (consumed, not hand-rolled) —
         :func:`reasoning.compose_paths` with ``start=term`` and ``min_hops=1``
         enumerates every bounded, acyclic path from ``term`` to each defining
         token, with full provenance. The transitive definitional content is the
         union of the reached ``object`` tokens.

      3. **Relation-type coherence** (consumed, not hand-rolled) — when a
         :class:`relation.RelationAlgebra` is supplied, each reached chain of
         defining relations is folded with
         :meth:`relation.RelationAlgebra.compose_path`. A branch whose fold
         escalates (:data:`relation.ESCALATE`) or yields no coherent relation
         (``None``) is *contested*: its token is withheld from the settled
         closure and the result is ``open=True``. With no algebra, coherence is
         not asserted and every acyclic branch is admitted.

    An **undefined** term (named by no definitional edge) returns
    ``defined=False`` with an empty closure — an explicit unknown, never a
    fabricated definition.
    """
    edge_list = _coerce_edges(edges)

    adjacency: dict[str, list[str]] = {}
    for e in edge_list:
        adjacency.setdefault(e.subject, []).append(e.object)

    defined = term in adjacency

    # ── undefined term: explicit unknown, never fabricated ──────────────────────
    if not defined:
        return ClosedDefinition(
            term=term, defined=False, tokens=frozenset(), open=False,
            reason=f"no definitional edge names {term!r} — undefined "
                   f"(explicit unknown, not a fabricated definition)",
        )

    # ── 1. cycle detection (added additively; does not loop) ────────────────────
    cycle = _find_definitional_cycle(adjacency, term)

    # ── 2. transitive reach via compose_paths (consumed, bounded, acyclic) ──────
    inferences = compose_paths(
        edge_list, start=term, min_hops=1,
        max_depth=max_depth, max_results=max_results,
    )

    settled: set[str] = set()
    contested: list[dict] = []
    admitted_paths: list[dict] = []

    for inf in inferences:
        chain = [hop["predicate"] for hop in inf.path]
        # ── 3. relation-type coherence along this reached chain ─────────────────
        if relations is not None:
            composed, escalated = relations.compose_path(chain)
            if escalated or composed is ESCALATE or composed is None:
                contested.append({
                    "object": inf.object,
                    "chain": list(chain),
                    "composed": "ESCALATE" if (escalated or composed is ESCALATE)
                    else None,
                })
                continue  # demoted to OPEN — not admitted into the settled closure
        settled.add(inf.object)
        admitted_paths.append(inf.as_dict())

    is_open = cycle is not None or bool(contested)

    if cycle is not None:
        reason = (f"definitional cycle reachable from {term!r}: "
                  + " → ".join(cycle) + " → OPEN (not expanded through the loop)")
    elif contested:
        reason = (f"{len(contested)} branch(es) contested (ESCALATE / no coherent "
                  f"definitional relation) → OPEN; settled closure withholds them")
    else:
        reason = (f"{term!r} closes to {len(settled)} defining token(s) over "
                  f"{len(admitted_paths)} acyclic definitional path(s)")

    return ClosedDefinition(
        term=term,
        defined=True,
        tokens=frozenset(settled),
        open=is_open,
        cycle=cycle,
        contested=tuple(contested),
        paths=tuple(admitted_paths),
        reason=reason,
    )
