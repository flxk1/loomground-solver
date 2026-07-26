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

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .dimensions import Dimension, compose, compose_weights


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
) -> list[Inference]:
    """Compose multi-hop paths into inferences.

    Walks directed paths (the object of one edge is the subject of the next),
    up to ``max_depth`` edges, with no repeated node (acyclic). Only paths of
    two or more hops produce an inference — a single edge is already a fact, not
    a derivation. Results are pruned below ``min_confidence`` and returned
    highest-confidence first, capped at ``max_results``.
    """
    adjacency: dict[str, list[Edge]] = {}
    for e in edges:
        adjacency.setdefault(e.subject, []).append(e)

    max_depth = max(2, int(max_depth))
    results: list[Inference] = []

    def walk(node: str, visited: tuple[str, ...], path: list[Edge]) -> None:
        if len(path) >= max_depth:
            return
        for e in adjacency.get(node, ()):
            if e.object in visited:
                continue  # acyclic
            new_path = path + [e]
            if len(new_path) >= 2:
                dim = new_path[0].dimension
                conf = new_path[0].weight
                for nxt in new_path[1:]:
                    dim = compose(dim, nxt.dimension)        # left-fold
                    conf = compose_weights(conf, nxt.weight)
                if conf >= min_confidence:
                    results.append(Inference(
                        subject=new_path[0].subject,
                        object=e.object,
                        dimension=dim,
                        confidence=conf,
                        hops=len(new_path),
                        dimension_chain=[h.dimension.value for h in new_path],
                        path=[{
                            "subject": h.subject, "predicate": h.predicate,
                            "object": h.object, "dimension": h.dimension.value,
                            "source_pair": h.source_pair,
                        } for h in new_path],
                    ))
            walk(e.object, visited + (e.object,), new_path)

    starts = [start] if start is not None else list(adjacency.keys())
    for s in starts:
        walk(s, (s,), [])

    results.sort(key=lambda i: i.confidence, reverse=True)
    return results[:max_results]
