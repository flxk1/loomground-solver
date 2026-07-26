# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Validated solver topology — the primitive that keeps a DERIVED solver
structure clean and governed.

A fixed flow (n8n, Power Automate) is authored once and walks the same nodes
every input. A Workspaces solver derives its structure from the problem's
fingerprints, so it is situational. The danger of derivation is arbitrary,
non-reproducible structure — the opposite of governable. This module makes
the derived structure a TYPED DAG whose validity is checked, so the
flexibility stays auditable:

  * it must be a DAG (no cycles, no dangling deps, no orphans);
  * governance rides on node KIND, not flow position — a ``judgment`` node
    may never be graded ``auto``; an important node stays in the human loop
    wherever the derivation places it;
  * execution order is a deterministic topological sort, so the same
    fingerprints yield the same structure AND the same order (stability —
    derived, not arbitrary).

The validator returns findings like :func:`workspaces.kg_export.validate_graph`,
and a valid topology projects to the same Cytoscape shape the rest of the
problem-solution graph uses, dependency edges visible.

Internal by design: consulted by the validators when a derived solver is checked; no operator surface of its own.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ._projection import _edge, _node

#: dependency relations between solver nodes (a small fixed vocabulary keeps
#: derived structures comparable rather than arbitrary).
DEP_RELATIONS = ("feeds", "conditions", "requires")

#: node kinds. 'judgment' is the governed kind — it cannot run unattended.
NODE_KINDS = ("solve", "judgment", "gate")

#: grades that keep a human in the loop (mirrors the matrix/control-form
#: light→form mapping: ask = single approver, block = stop).
HUMAN_GRADES = ("ask", "block")


@dataclass
class SolverNode:
    id: str
    fingerprint: dict[str, Any]
    solver: str
    kind: str = "solve"
    grade: str = "auto"
    warrant: str = ""          # why this node exists (accountability): see
                               # accountability.WARRANT_KINDS — empty = arbitrary

    def to_node(self) -> dict[str, Any]:
        return _node(self.id, self.solver or self.id,
                     {"solve": "schema_step", "judgment": "reading",
                      "gate": "resolution"}.get(self.kind, "kg-node"),
                     {"kind": self.kind, "grade": self.grade,
                      "issue_type": self.fingerprint.get("issue_type", "")})


@dataclass
class Dep:
    src: str
    dst: str
    relation: str = "feeds"


def _validate(nodes: list[SolverNode], deps: list[Dep],
              roots: Optional[list[str]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    ids = {n.id for n in nodes}

    # V3 dangling deps + unknown relations
    for d in deps:
        if d.src not in ids or d.dst not in ids:
            findings.append({"kind": "dangling-dep",
                             "id": f"{d.src}->{d.dst}"})
        if d.relation not in DEP_RELATIONS:
            findings.append({"kind": "unknown-relation",
                             "id": f"{d.src}->{d.dst}", "value": d.relation})

    # V4 governance: a judgment node may not be auto-graded
    for n in nodes:
        if n.kind == "judgment" and n.grade not in HUMAN_GRADES:
            findings.append({"kind": "ungoverned-judgment", "id": n.id,
                             "grade": n.grade})
        if n.kind not in NODE_KINDS:
            findings.append({"kind": "unknown-node-kind", "id": n.id,
                             "value": n.kind})

    # V1 cycle detection (only over edges between known nodes)
    adj: dict[str, list[str]] = {n.id: [] for n in nodes}
    for d in deps:
        if d.src in ids and d.dst in ids:
            adj[d.src].append(d.dst)
    state: dict[str, int] = {}        # 0=unseen 1=on-stack 2=done

    def _walk(u: str) -> bool:
        state[u] = 1
        for v in adj[u]:
            if state.get(v, 0) == 1:
                return True
            if state.get(v, 0) == 0 and _walk(v):
                return True
        state[u] = 2
        return False

    if any(state.get(n.id, 0) == 0 and _walk(n.id) for n in nodes):
        findings.append({"kind": "cycle", "id": "topology"})

    # V2 orphans: in a 'feeds' DAG the root is a SINK — every node should
    # feed, directly or transitively, into a root. So connectivity is
    # reachability of a root by following edges FORWARD (a node can reach a
    # root). Compute it as reverse-BFS from the roots over reversed edges.
    if roots is None:
        # default roots = sinks (no outgoing feed)
        srcs = {d.src for d in deps if d.src in ids and d.dst in ids}
        roots = [n.id for n in nodes if n.id not in srcs]
    radj: dict[str, list[str]] = {n.id: [] for n in nodes}
    for d in deps:
        if d.src in ids and d.dst in ids:
            radj[d.dst].append(d.src)          # reversed: dst <- src
    feeds_a_root: set[str] = set()
    stack = list(roots)
    while stack:
        u = stack.pop()
        if u in feeds_a_root:
            continue
        feeds_a_root.add(u)
        stack.extend(radj.get(u, []))
    for n in nodes:
        if n.id not in feeds_a_root:
            findings.append({"kind": "orphan", "id": n.id})
    return findings


def validate_topology(nodes: list[SolverNode], deps: list[Dep], *,
                      roots: Optional[list[str]] = None) -> list[dict[str, Any]]:
    """Public validation: structural + governance findings for a derived
    solver topology, without building the graph projection."""
    return _validate(nodes, deps, roots)


def topo_order(nodes: list[SolverNode], deps: list[Dep]) -> list[str]:
    """Deterministic topological order: a node follows everything that feeds
    it. Ties broken by id so the same fingerprints yield the same order. On a
    cycle, returns the acyclic prefix (the validator reports the cycle)."""
    ids = [n.id for n in nodes]
    indeg = {i: 0 for i in ids}
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for d in deps:
        if d.src in indeg and d.dst in indeg:
            adj[d.src].append(d.dst)
            indeg[d.dst] += 1
    ready = sorted(i for i in ids if indeg[i] == 0)
    order: list[str] = []
    while ready:
        u = ready.pop(0)
        order.append(u)
        for v in sorted(adj[u]):
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)
        ready.sort()
    return order


def build_topology(nodes: list[SolverNode], deps: list[Dep], *,
                   roots: Optional[list[str]] = None) -> dict[str, Any]:
    """Validate a derived solver topology and, if clean, project it to the
    shared Cytoscape graph shape with dependency edges visible. ``ok`` is
    False on any structural or governance violation; the graph is still
    returned for inspection."""
    findings = _validate(nodes, deps, roots)
    blocking = {"cycle", "dangling-dep", "unknown-relation",
                "ungoverned-judgment", "unknown-node-kind"}
    ok = not any(f["kind"] in blocking for f in findings)

    graph_nodes = [n.to_node() for n in nodes]
    ids = {n.id for n in nodes}
    graph_edges = []
    for d in deps:
        if d.src in ids and d.dst in ids:
            graph_edges.append(_edge({
                "subject": d.src, "predicate": d.relation, "object": d.dst,
                "dimension": "structural",
                "note": f"dependency: {d.src} {d.relation} {d.dst}"}))
    return {"ok": ok, "findings": findings,
            "order": topo_order(nodes, deps),
            "graph": {"nodes": graph_nodes, "edges": graph_edges}}
