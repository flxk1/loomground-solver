"""Neutral structural-evidence compilers; graph-specific compilers are adapters."""
from __future__ import annotations

from .dimensions import Dimension

EDGE_SCHEMA = "reasoning.edges/v1"
_DIMENSIONS = {d.value for d in Dimension}


class NeutralStructuralCompiler:
    """Compile a plain edge-list schema with optional candidate attack links."""

    def supports(self, schema: str) -> bool:
        return schema in ("", EDGE_SCHEMA)

    def compile(self, candidate) -> dict:
        data = dict(candidate.structural_evidence or {})
        schema = str(data.get("schema", ""))
        if not self.supports(schema):
            raise ValueError(f"unsupported structural schema: {schema}")
        edges = []
        for edge in data.get("edges", ()):
            e = dict(edge)
            if not all(str(e.get(k, "")).strip() for k in ("subject", "predicate", "object")):
                raise ValueError("structural edge needs subject, predicate, and object")
            dimension = str(e.get("dimension", "relational"))
            if dimension not in _DIMENSIONS:
                raise ValueError(f"unknown edge dimension: {dimension}")
            e["dimension"] = dimension
            edges.append(e)
        attacks = []
        for attack in data.get("attacks", ()):
            if not isinstance(attack, (list, tuple)) or len(attack) != 2:
                raise ValueError("attack must be a two-item sequence")
            attacks.append((str(attack[0]), str(attack[1])))
        pair = {
            "id": candidate.candidate_id,
            "problem": {"id": f"{candidate.candidate_id}:problem",
                        "summary": candidate.claim, "facets": {}},
            "solution": {"id": candidate.candidate_id,
                         "problem_id": f"{candidate.candidate_id}:problem",
                         "body": candidate.claim, "confidence": 1.0},
            "edges": edges,
        }
        return {"pairs": [pair], "attacks": attacks, "schema": schema or EDGE_SCHEMA}


class CompilerRegistry:
    """Ordered registry selecting the first compiler that advertises a schema."""

    def __init__(self, compilers=()):
        self.compilers = list(compilers) or [NeutralStructuralCompiler()]

    def resolve(self, schema: str):
        for compiler in self.compilers:
            if compiler.supports(schema):
                return compiler
        raise KeyError(f"no structural compiler for {schema!r}")

    def compile(self, candidate) -> dict:
        schema = str((candidate.structural_evidence or {}).get("schema", ""))
        return self.resolve(schema).compile(candidate)
