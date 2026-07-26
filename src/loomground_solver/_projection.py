# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Pure graph-projection helpers, extracted from the Workspace ``kg_export``.

Only the substrate-neutral pieces the solver topology needs live here: the
node/edge builders (``_node``, ``_edge``), the structural/provenance validator
(``validate_graph``), and the small colour/label tables and ``_pretty`` helper
they call. Everything is pure stdlib — no corpus, no governance, no I/O — so
the topology projection stays importable unchanged by any host.
"""

from __future__ import annotations

# 5D dimension → colour (shared by every viewer so the legend is stable)
DIMENSION_COLOR = {
    "structural":  "#2563eb",   # blue   — how it is built
    "causal":      "#dc2626",   # red    — what makes it bind
    "intentional": "#7c3aed",   # purple — what it is for
    "temporal":    "#16a34a",   # green  — when it governs
    "relational":  "#64748b",   # slate  — what it is linked to
}

# node kind → colour
KIND_COLOR = {
    "system": "#0f172a", "supranational": "#0f172a", "state": "#1e293b",
    "international_regime": "#334155", "regulator": "#b45309",
    "standards_body": "#0891b2", "instrument": "#a16207", "class": "#475569",
    "source": "#a16207", "legal_person": "#be185d", "rule": "#9333ea",
    "norm": "#9333ea", "kg-node": "#475569",
    # case-trace kinds (problem-solution graph): the walk through the nodes
    "question": "#0ea5e9", "fact": "#16a34a", "gap": "#dc2626",
    "schema_step": "#7c3aed", "reading": "#f59e0b", "resolution": "#0f172a",
    "subproblem": "#9333ea", "gap-bearing": "#dc2626",
}


# plain-language meaning of each reasoning dimension (for legends/tooltips)
DIMENSION_MEANING = {
    "structural":  "how the legal order is built — membership, hierarchy, composition",
    "causal":      "what brings the law to bear — application, transposition, citation",
    "intentional": "what a body or instrument is for — mandate, presumption of conformity",
    "temporal":    "when it governs — supersession, entry into force",
    "relational":  "what it is linked to — equivalence, correspondence",
}

# predicate slug → human-readable verb phrase
PRED_LABEL = {
    "member_of": "is a member of", "member-of": "is a member of",
    "has_primacy_over": "has primacy over", "outranks": "outranks",
    "applies_in": "applies in", "enforces": "enforces",
    "established_by": "established by", "established-by": "established by",
    "adopted_by": "adopted by", "party_to": "is party to", "bound_by": "is bound by",
    "equivalent_to": "adequacy / equivalent to", "supervises": "supervises",
    "supersedes": "supersedes (replaces)",
    "presumes_conformity": "raises a presumption of conformity for",
    "presumes-conformity": "raises a presumption of conformity for",
    "descends_from": "derives from", "descends-from": "derives from",
    "incorporates": "incorporates", "transposes": "transposes",
    "corresponds-to": "corresponds to", "corresponds_to": "corresponds to",
    "instance-of": "is a kind of", "instance_of": "is a kind of",
    "belongs-to": "belongs to", "belongs_to": "belongs to",
    "cites": "cites", "governed_by": "is governed by", "enforced_by": "is enforced by",
    "decomposes_to": "decomposes to",
    "feeds": "feeds", "conditions": "conditions", "requires": "requires",
}

# source-class slug → readable phrase
_CLASS_PRETTY = {
    "supranational_regulation": "EU Regulation (directly applicable)",
    "supranational_directive": "EU Directive (binds via transposition)",
    "supranational_primary": "EU primary law (Treaties / Charter)",
    "national_statute": "national statute", "national_regulation": "national regulation",
    "constitution": "constitution", "case_law": "case law",
    "international_treaty": "international treaty",
    "customary_international": "customary international law",
    "technical_standard": "technical standard", "soft_law": "soft law",
}


def _pretty(s: str) -> str:
    for k, v in _CLASS_PRETTY.items():
        s = s.replace(k, v)
    return s.replace("_", " ").replace(":", " — ")


def _node(nid: str, label: str, kind: str, facets: dict | None = None) -> dict:
    return {"data": {"id": nid, "label": _pretty(label), "kind": kind,
                     "kind_label": kind.replace("_", " "),
                     "color": KIND_COLOR.get(kind, "#475569"),
                     "facets": facets or {}}}


def _edge(e: dict) -> dict:
    dim = e.get("dimension", "relational")
    pred = e["predicate"]
    return {"data": {"id": f"{e['subject']}|{pred}|{e['object']}",
                     "source": e["subject"], "target": e["object"],
                     "label": pred, "rel_label": PRED_LABEL.get(pred, pred.replace("_", " ")),
                     "dimension": dim, "dim_meaning": DIMENSION_MEANING.get(dim, ""),
                     "color": DIMENSION_COLOR.get(dim, "#64748b"),
                     "note": e.get("note", "")}}


def validate_graph(cyto: dict) -> dict:
    """Validate a graph for *structural* well-formedness and *provenance*
    completeness — the two things a human can check before trusting the picture.

    Structural: no dangling edge, every dimension known, every node labelled.
    Provenance: every edge carries a `basis` (a citable justification), and every
    corpus entity (instrument/regulator/standards body) carries a source URL.
    The substantive legal truth of each edge still needs a human — but this report
    tells you *which* claims are even checkable (have a basis) and which are bare."""
    ids = {n["data"]["id"] for n in cyto["nodes"]}
    findings: list[dict] = []
    for e in cyto["edges"]:
        d = e["data"]
        if d["source"] not in ids or d["target"] not in ids:
            findings.append({"kind": "dangling-edge", "id": d["id"]})
        if d.get("dimension") not in DIMENSION_COLOR:
            findings.append({"kind": "unknown-dimension", "id": d["id"], "value": d.get("dimension")})
        if not (d.get("note") or "").strip():
            findings.append({"kind": "edge-without-basis", "id": d["id"],
                             "rel": d.get("rel_label", d.get("label"))})
    for n in cyto["nodes"]:
        nd = n["data"]
        if not (nd.get("label") or "").strip():
            findings.append({"kind": "node-without-label", "id": nd["id"]})
        if nd["kind"] in ("instrument", "regulator", "standards_body") and not nd.get("facets", {}).get("url"):
            findings.append({"kind": "entity-without-source-url", "id": nd["id"]})
    ne = len(cyto["edges"]) or 1
    with_basis = ne - sum(1 for f in findings if f["kind"] == "edge-without-basis")
    return {
        "ok": not any(f["kind"] in ("dangling-edge", "unknown-dimension", "node-without-label")
                      for f in findings),
        "nodes": len(cyto["nodes"]), "edges": len(cyto["edges"]),
        "edges_with_basis_pct": round(100 * with_basis / ne, 1),
        "counts": {k: sum(1 for f in findings if f["kind"] == k)
                   for k in {f["kind"] for f in findings}},
        "findings": findings[:50],
    }
