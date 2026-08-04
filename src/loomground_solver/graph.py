# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Graph-traversal and graph-prep primitives over the dimensioned edge graph.

:mod:`loomground_solver.reasoning` *composes* directed paths into inferences.
This module holds the neighbourhood and preparation primitives that sit around
that composition — the plumbing a consumer would otherwise hand-roll before or
instead of reaching for :func:`compose_paths`:

* :func:`neighborhood` — a bounded breadth-first neighbourhood of a focus node.
  An edge connects *both* its endpoints into the frontier (the graph is walked
  undirected for reach), so the neighbourhood is the set of nodes within
  ``depth`` hops of the focus and the edges touched along the way.
* :func:`to_undirected` — the undirected-preparation step: for every edge, add
  its reverse, deduplicated, so a directed-only walker (:func:`compose_paths`)
  can traverse either direction.

Both operate on solver :class:`~loomground_solver.reasoning.Edge` objects and
are pure, deterministic and bounded, in the same spirit as
:func:`compose_paths`: given the same input list they return the same output in
the same order on every run, and the work is bounded by ``depth`` (never by the
number of distinct paths the graph admits).

Direct single-hop links are *not* a separate concern here: a one-hop connection
is produced by :func:`compose_paths` with ``min_hops=1`` (a single edge recorded
as a 1-hop inference), so a consumer that wants "direct edge, else composed
path" makes one bounded call rather than a shortcut plus a fallback.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from .dimensions import Dimension
from .reasoning import Edge


def _dimension_filter(dimensions: Optional[Iterable[Any]]) -> Optional[frozenset[str]]:
    """Normalise a dimension filter into a set of dimension *value* strings.

    Accepts :class:`~loomground_solver.dimensions.Dimension` members or their
    string values interchangeably, so a consumer may pass either. ``None``
    (the caller declined to filter) is passed through as ``None`` — meaning *no
    filter*, which is not the same as an empty filter (which would exclude
    everything). An unrecognised dimension name is kept as-is: it simply matches
    no edge rather than raising, so a stale filter narrows the result instead of
    breaking the call.
    """
    if dimensions is None:
        return None
    wanted: set[str] = set()
    for d in dimensions:
        wanted.add(d.value if isinstance(d, Dimension) else str(d))
    return frozenset(wanted)


def neighborhood(
    edges: list[Edge],
    focus: str,
    *,
    depth: int = 2,
    dimensions: Optional[Iterable[Any]] = None,
) -> dict[str, Any]:
    """Return the bounded neighbourhood of ``focus`` over ``edges``.

    A breadth-first sweep: the reached set is seeded with ``focus``, then for
    ``depth`` rounds every edge whose subject *or* object is already reached is
    selected and both of its endpoints are added to the reached set. An edge
    therefore connects both endpoints into the frontier — the graph is walked
    *undirected* for reach, even though the edges themselves stay directed in the
    result — so after ``depth`` rounds the reached set is every node within
    ``depth`` hops of ``focus`` in either direction.

    ``depth`` is clamped to ``>= 0``; ``depth=0`` yields the focus alone with no
    edges. ``dimensions`` optionally restricts the sweep to edges whose dimension
    is in the given set (:class:`~loomground_solver.dimensions.Dimension` members
    or their string values, mixed freely); ``None`` means no restriction.

    The result is::

        {"focus": focus,
         "nodes": [<reached node ids, sorted>],
         "edges": [<selected Edge objects, in discovery order>]}

    This is intentionally *node-id* shaped, not record shaped: the primitive
    owns no domain records, so it returns the reached ids and the edges touched
    and leaves mapping ids back to domain nodes to the caller. ``focus`` is
    always present in ``nodes`` (an isolated or absent focus yields
    ``nodes == [focus]`` and ``edges == []``).

    Deterministic: ``nodes`` is sorted and ``edges`` preserves the input order
    in which edges were first selected, so the same input list always produces
    the same output. Duplicate edges in the input are selected at most once.
    """
    dim_filter = _dimension_filter(dimensions)
    pool = [
        e for e in edges
        if dim_filter is None or e.dimension.value in dim_filter
    ]

    reached: set[str] = {focus}
    selected: list[Edge] = []
    seen: set[Edge] = set()
    for _ in range(max(0, int(depth))):
        frontier = set(reached)
        for e in pool:
            if e.subject in frontier or e.object in frontier:
                reached.add(e.subject)
                reached.add(e.object)
                if e not in seen:
                    seen.add(e)
                    selected.append(e)

    return {
        "focus": focus,
        "nodes": sorted(reached, key=str),
        "edges": selected,
    }


def to_undirected(edges: list[Edge]) -> list[Edge]:
    """Return ``edges`` plus a reverse of each, deduplicated.

    For every edge ``subject →[predicate]→ object`` a reverse edge
    ``object →[predicate]→ subject`` is added, carrying the same dimension,
    weight and source-pair provenance, so a directed-only walker
    (:func:`compose_paths`) can traverse the graph in either direction — the
    undirected-graph preparation a consumer would otherwise inline before
    composing.

    Deduplicated and deterministic: the original edges are emitted first in
    input order (with any exact duplicates dropped), then the reverses in input
    order, each added only if that exact edge is not already present. So an edge
    whose reverse already exists in the input contributes no new edge, and a
    self-loop (``subject == object``) is never doubled.
    """
    out: list[Edge] = []
    seen: set[Edge] = set()

    def _add(e: Edge) -> None:
        if e not in seen:
            seen.add(e)
            out.append(e)

    for e in edges:
        _add(e)
    for e in edges:
        _add(Edge(
            subject=e.object,
            predicate=e.predicate,
            object=e.subject,
            dimension=e.dimension,
            weight=e.weight,
            source_pair=e.source_pair,
        ))
    return out
