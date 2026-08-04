# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Reasoning over the five-dimensional edge graph.

A folder's memory is a graph of typed edges (see workspaces.dimensions): each edge
relates two things along a reasoning dimension — structural, causal,
intentional, temporal, or relational. Reasoning here means *composing* edges
along a path: if A relates to B and B relates to C, what relates A to C, and in
which dimension?

The dimension of a composed path is the left-fold of the composition algebra
(``compose``). Left-fold — walking the path start to end — is the canonical
order, because the algebra is not fully associative (two of 125 dimension
triples differ by grouping; see tests/test_5d_nd_stress.py), so the order must
be fixed and documented. The confidence of a path is the product of its edge
weights (two 0.8 steps -> 0.64): longer or weaker chains are less certain.

Every inference carries its full provenance — the ordered edges it was composed
from and the per-hop dimension chain — so a derived conclusion can be traced
back to the source edges. That provenance is what makes reasoning auditable
when an inference is recorded to the signed log.

This module is pure: it builds a graph from pair dicts and returns inferences.
Recording inferences to the audit log lives in the MCP layer.
"""

from __future__ import annotations

import heapq
import itertools
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .dimensions import Dimension, compose, compose_weights

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Edge:
    """A directed, dimensioned edge between two nodes."""

    subject: str
    predicate: str
    object: str
    dimension: Dimension
    weight: float = 1.0
    source_pair: str = ""   # id of the pair this edge came from (provenance)


@dataclass
class Inference:
    """A derived relation composed from a path of edges."""

    subject: str
    object: str
    dimension: Dimension          # composed dimension (left-fold)
    confidence: float             # product of edge weights along the path
    hops: int
    dimension_chain: list[str] = field(default_factory=list)   # per-hop dims
    path: list[dict[str, Any]] = field(default_factory=list)   # source edges, in order

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "object": self.object,
            "dimension": self.dimension.value,
            "confidence": round(self.confidence, 4),
            "hops": self.hops,
            "dimension_chain": list(self.dimension_chain),
            "path": list(self.path),
        }


class InferenceList(list):
    """A ``list`` of :class:`Inference` that also reports whether it was capped.

    It *is* a list — equality, iteration, indexing, ``len`` and slicing all
    behave exactly as before, so every existing caller is unaffected. The extra
    ``truncated`` attribute is the non-breaking truncation signal: it is ``True``
    when more paths qualified than ``max_results`` and the lowest-ranked ones
    were dropped, ``False`` otherwise. A truncation also emits a
    ``logging.WARNING`` on the ``loomground_solver.reasoning`` logger, so the cap
    is observable whether the caller inspects the flag or watches the log.
    """

    #: class-level default so ``InferenceList()`` is always safe to read
    truncated: bool = False


def extract_edges(pairs: Iterable[dict[str, Any]]) -> list[Edge]:
    """Pull every well-formed dimensioned edge out of a list of pair dicts.

    Each edge's weight defaults to the source pair's solution confidence, so a
    composed inference inherits the certainty of the evidence it rests on.
    Malformed edges are skipped, not raised on.
    """
    out: list[Edge] = []
    for p in pairs or []:
        if not isinstance(p, dict):
            continue
        weight = 1.0
        sol = p.get("solution")
        if isinstance(sol, dict):
            try:
                weight = float(sol.get("confidence", 1.0))
            except (TypeError, ValueError):
                weight = 1.0
        pair_id = str(p.get("id", ""))
        edges = p.get("edges")
        if not isinstance(edges, list):
            continue
        for e in edges:
            if not isinstance(e, dict):
                continue
            subj, pred, obj = e.get("subject"), e.get("predicate"), e.get("object")
            dim_val = e.get("dimension")
            if not (subj and obj and dim_val in {d.value for d in Dimension}):
                continue
            out.append(Edge(
                subject=str(subj), predicate=str(pred or ""), object=str(obj),
                dimension=Dimension(dim_val),
                weight=max(0.0, min(1.0, weight)),
                source_pair=pair_id,
            ))
    return out


def compose_paths(
    edges: list[Edge],
    *,
    start: Optional[str] = None,
    max_depth: int = 3,
    min_confidence: float = 0.0,
    max_results: int = 200,
    min_hops: int = 2,
) -> InferenceList:
    """Compose multi-hop paths into inferences.

    Walks directed paths (the object of one edge is the subject of the next),
    up to ``max_depth`` edges, with no repeated node (acyclic). By default only
    paths of two or more hops produce an inference — a single edge is already a
    fact, not a derivation. Results are pruned below ``min_confidence`` and
    returned highest-confidence first, capped at ``max_results``.

    ``min_hops`` (default ``2``) sets the shortest path that counts as a result;
    it is clamped to ``>= 1``. The default reproduces the historical output
    exactly (derivations only). Pass ``min_hops=1`` to *also* record direct
    single-hop links — a lone edge ``src →[predicate]→ dst`` recorded as a
    1-hop inference (dimension = the edge's own dimension, confidence = its
    weight) — so a consumer wanting "direct edge, else composed path" makes one
    bounded call instead of a shortcut plus a fallback. Raising ``min_hops``
    above ``2`` reports only longer chains.

    The other caps are configurable too; the defaults (``max_depth=3``,
    ``min_confidence=0.0``, ``max_results=200``, ``min_hops=2``) reproduce the
    historical output exactly, so changing them is opt-in. On a real
    regulation's graph (thousands
    of edges) the walk stays bounded in two ways so it never materialises an
    exponential frontier:

    * **Subtree pruning.** Confidence is the product of edge weights (each in
      ``[0, 1]``), so it is monotonically non-increasing along a path. Once the
      running confidence drops below ``min_confidence`` the whole subtree is
      abandoned — every deeper path would be pruned at recording time anyway.
    * **Running best-of cap.** Only the top ``max_results`` inferences by
      confidence are retained during the walk (a bounded min-heap), so memory is
      ``O(max_results)`` regardless of how many paths the graph admits.

    Returns an :class:`InferenceList` — a plain ``list`` of :class:`Inference`
    with an extra ``truncated`` flag that is ``True`` when the ``max_results``
    cap dropped lower-ranked paths (a warning is also logged). Ranking is
    deterministic: confidence descending, ties broken by walk order (the order
    paths are discovered), so the retained top-N is stable across runs.
    """
    adjacency: dict[str, list[Edge]] = {}
    for e in edges:
        adjacency.setdefault(e.subject, []).append(e)

    max_depth = max(2, int(max_depth))
    cap = max(0, int(max_results))
    floor_hops = max(1, int(min_hops))

    # Bounded min-heap of the best-so-far inferences. Each entry is
    # ``(confidence, -seq, inference)``; ``seq`` is a per-walk discovery counter,
    # so the ordering key ``(confidence, -seq)`` is always unique (the
    # Inference itself is never compared). The smallest entry — lowest
    # confidence, and among equals the latest-discovered — is the one evicted
    # first, i.e. we keep the highest-confidence / earliest-discovered paths.
    heap: list[tuple[float, int, Inference]] = []
    seq_counter = itertools.count()
    truncated = False

    def _record(inf: Inference) -> None:
        nonlocal truncated
        entry = (inf.confidence, -next(seq_counter), inf)
        if cap <= 0:
            truncated = True
            return
        if len(heap) < cap:
            heapq.heappush(heap, entry)
        else:
            heapq.heappushpop(heap, entry)
            truncated = True

    def walk(node: str, visited: tuple[str, ...], path: list[Edge],
             dim: Optional[Dimension], conf: float) -> None:
        nonlocal truncated
        if len(path) >= max_depth:
            return
        for e in adjacency.get(node, ()):
            if e.object in visited:
                continue  # acyclic
            # Extend the left-fold incrementally instead of recomputing it.
            if dim is None:                       # first edge on the path
                new_dim, new_conf = e.dimension, e.weight
            else:
                new_dim = compose(dim, e.dimension)          # left-fold
                new_conf = compose_weights(conf, e.weight)
            # ``new_conf`` is a monotone upper bound on every inference this
            # subtree can yield: confidence is a product of edge weights in
            # ``[0, 1]``, so every deeper path is ``<= new_conf``. Two prunes
            # rest on that bound, and neither changes the result set — they
            # only skip work that could not survive to the output:
            if new_conf < min_confidence:
                # Below the caller's floor; nothing deeper can rise to meet it.
                continue
            if cap > 0 and len(heap) >= cap and new_conf < heap[0][0]:
                # Branch-and-bound: the best-of heap is full and this path
                # already sits below its lowest retained confidence, so neither
                # it nor any deeper path can displace a kept inference. Skipping
                # the subtree is result-identical to walking it (every path in
                # it would be recorded then immediately evicted) — but a
                # qualifying path is being dropped, so raise the truncation
                # signal exactly as that eviction would. This is what bounds the
                # walk's *time*, not just its memory, on high-fan-out graphs.
                truncated = True
                continue
            new_path = path + [e]
            if len(new_path) >= floor_hops:
                _record(Inference(
                    subject=new_path[0].subject,
                    object=e.object,
                    dimension=new_dim,
                    confidence=new_conf,
                    hops=len(new_path),
                    dimension_chain=[h.dimension.value for h in new_path],
                    path=[{
                        "subject": h.subject, "predicate": h.predicate,
                        "object": h.object, "dimension": h.dimension.value,
                        "source_pair": h.source_pair,
                    } for h in new_path],
                ))
            walk(e.object, visited + (e.object,), new_path, new_dim, new_conf)

    starts = [start] if start is not None else list(adjacency.keys())
    for s in starts:
        walk(s, (s,), [], None, 1.0)

    # Highest confidence first; ties keep walk order (``-(-seq)`` -> seq asc).
    ordered = sorted(heap, key=lambda t: (-t[0], -t[1]))
    out = InferenceList(t[2] for t in ordered)
    out.truncated = truncated
    if truncated:
        _LOG.warning(
            "compose_paths truncated results at max_results=%d "
            "(more paths qualified; lowest-confidence inferences dropped)",
            cap,
        )
    return out
