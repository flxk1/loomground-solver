# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Five-dimensional edge model for the knowledge graph.

Every edge between two notes carries a *dimension* — the kind of reasoning
the edge represents. Five dimensions cover the ways one thing relates to
another:

    STRUCTURAL   — how is it built?      (part-of, contains, depends-on)
    CAUSAL       — why does it happen?   (triggers, causes, enables, prevents)
    INTENTIONAL  — what is it for?       (aims-at, justifies, motivates)
    TEMPORAL     — when does it occur?   (before, during, after, succeeds)
    RELATIONAL   — what is it linked to? (similar, contrasts, associated)

A dimensioned graph can be traversed by reasoning type — follow a causal
chain, decompose a structure, trace a timeline — instead of matching words
only. The composition table says which dimension governs a two-step
inference: if A relates to B structurally and B relates to C causally, the
A→C inference is causal.

This module is self-contained: it defines the model and the algebra, and
does not touch the mutation log, the audit chain, or storage. Edges are
labelled with a dimension by the extractor that creates them (see
``classify_predicate``); retrieval and traversal consume the label.

Federation adapter
------------------
The enum string values here are identical to the cell concept-graph used in
the Federation project, so a dimensioned Workspace edge maps one-to-one onto a
Federation cell edge with no translation. If a Federation backend is wired
in later, this module is the seam: keep the string values and the
composition table in sync and the two graphs interoperate directly.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional


class Dimension(str, Enum):
    """The five reasoning dimensions an edge can carry."""

    STRUCTURAL = "structural"
    CAUSAL = "causal"
    INTENTIONAL = "intentional"
    TEMPORAL = "temporal"
    RELATIONAL = "relational"


# Default for any edge whose dimension is unknown or unset. Relational is the
# safe floor: "these two things are linked" is always true of an edge.
DEFAULT_DIMENSION = Dimension.RELATIONAL


# ── Composition algebra ──────────────────────────────────────────
# Read as: (edge1.dimension, edge2.dimension) -> composed dimension.
# "If I know A through dimension X and B through dimension Y, which
#  dimension governs the A->B inference?"
# Ported verbatim from the Federation cell algebra so the two stay aligned.

_S = Dimension.STRUCTURAL
_C = Dimension.CAUSAL
_I = Dimension.INTENTIONAL
_T = Dimension.TEMPORAL
_R = Dimension.RELATIONAL

COMPOSITION_TABLE: dict[tuple[Dimension, Dimension], Dimension] = {
    (_S, _S): _S, (_S, _C): _C, (_S, _I): _I, (_S, _T): _T, (_S, _R): _S,
    (_C, _S): _C, (_C, _C): _C, (_C, _I): _I, (_C, _T): _T, (_C, _R): _C,
    (_I, _S): _S, (_I, _C): _C, (_I, _I): _I, (_I, _T): _T, (_I, _R): _I,
    (_T, _S): _S, (_T, _C): _C, (_T, _I): _I, (_T, _T): _T, (_T, _R): _T,
    (_R, _S): _S, (_R, _C): _C, (_R, _I): _I, (_R, _T): _T, (_R, _R): _R,
}


def compose(a: Dimension, b: Dimension) -> Dimension:
    """Return the dimension governing a two-step inference across ``a`` then ``b``."""
    return COMPOSITION_TABLE[(Dimension(a), Dimension(b))]


def compose_weights(w1: float, w2: float) -> float:
    """Compose two edge confidences. Multiplicative: two 0.8 steps -> 0.64."""
    return w1 * w2


# ── Predicate classification ─────────────────────────────────────
# Maps an edge predicate (the verb of a triple) to its dimension by keyword.
# Heuristic and intentionally small; an extractor that knows its domain
# should set the dimension explicitly rather than rely on this fallback.

_KEYWORDS: dict[Dimension, tuple[str, ...]] = {
    Dimension.STRUCTURAL: (
        "part-of", "part_of", "contains", "component", "depends-on",
        "depends_on", "has-part", "belongs-to", "composed-of", "subclass",
        "instance-of", "member-of",
    ),
    Dimension.CAUSAL: (
        "causes", "cause", "triggers", "trigger", "enables", "enable",
        "prevents", "prevent", "leads-to", "results-in", "produces",
        "requires", "depends-causally", "blocks",
    ),
    Dimension.INTENTIONAL: (
        "aims-at", "aims_at", "justifies", "justify", "motivates", "motivate",
        "intended-for", "purpose", "goal", "in-order-to", "so-that",
        "serves", "objective",
    ),
    Dimension.TEMPORAL: (
        "before", "after", "during", "succeeds", "precedes", "follows",
        "then", "next", "while", "since", "until", "expires", "starts",
        "ends", "scheduled",
    ),
    Dimension.RELATIONAL: (
        "similar", "similar-to", "contrasts", "contrast-with", "associated",
        "related-to", "references", "cites", "see-also", "compares",
        "analogous",
    ),
}


# ── Query intent ─────────────────────────────────────────────────
# Cues that hint which dimension a natural-language question leans toward, so
# ordinary "ask a folder" retrieval can quietly prefer pairs whose edges carry
# that dimension. Checked in order; explicit-purpose phrases beat a stray
# "why". Returns None when no cue fires — then retrieval is unchanged.

_QUERY_CUES: list[tuple[Dimension, tuple[str, ...]]] = [
    (Dimension.INTENTIONAL, (
        "what is it for", "what's it for", "what is this for", "purpose of",
        "the purpose", "in order to", "so that", "intended to", "goal of",
        "objective", "what is the point", "meant to",
    )),
    (Dimension.CAUSAL, (
        "why", "because", "what causes", "cause of", "causes", "reason",
        "leads to", "result of", "due to", "what makes", "what triggers",
    )),
    (Dimension.STRUCTURAL, (
        "how is", "how does it work", "structure of", "made of", "part of",
        "parts of", "component", "depends on", "built", "composed of",
        "consists of", "made up of",
    )),
    (Dimension.TEMPORAL, (
        "when", "timeline", "sequence", "in what order", "order of", "before",
        "after", "history of", "evolution of", "what happened first",
    )),
    (Dimension.RELATIONAL, (
        "similar to", "related to", "compare", "comparison", "associated",
        "connection between", "relationship between", "like ",
    )),
]


# "what … for?" / "what … used for" is a purpose question even with a noun in
# the middle that breaks a fixed-substring match.
_PURPOSE_RE = re.compile(r"\bwhat\b.{0,40}\bfor\b\s*\??\s*$|for what purpose")


def classify_query_dimension(query: str) -> Optional[Dimension]:
    """Infer the dimension a question leans toward, or None if no cue fires."""
    if not query:
        return None
    q = " " + query.strip().lower() + " "
    if _PURPOSE_RE.search(q.strip()):
        return Dimension.INTENTIONAL
    for dim, cues in _QUERY_CUES:
        for cue in cues:
            if cue in q:
                return dim
    return None


def classify_predicate(predicate: str) -> Dimension:
    """Map an edge predicate to a dimension by keyword match.

    Normalises the predicate (lowercase, spaces -> hyphens) and matches the
    keyword tables in priority order structural -> causal -> intentional ->
    temporal -> relational. Returns ``DEFAULT_DIMENSION`` (relational) when
    nothing matches.
    """
    if not predicate:
        return DEFAULT_DIMENSION
    norm = predicate.strip().lower().replace(" ", "-").replace("_", "-")
    for dim in (
        Dimension.STRUCTURAL,
        Dimension.CAUSAL,
        Dimension.INTENTIONAL,
        Dimension.TEMPORAL,
        Dimension.RELATIONAL,
    ):
        for kw in _KEYWORDS[dim]:
            k = kw.replace("_", "-")
            if k == norm or k in norm:
                return dim
    return DEFAULT_DIMENSION
