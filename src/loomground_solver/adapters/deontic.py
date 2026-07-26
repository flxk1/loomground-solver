"""Built-in deontic reference adapter to Solver 5D+nD input.

Projects deontic statements (O/P/F over a bearer:action, with the Hohfeld
incident) into Solver's native ``SolverProjection`` — one dimensioned edge per
norm, on the axis the deontic composition contract declares. It consumes the
published deontic surface (``parse``/``project``, the ``contract`` affinity, the
vocabulary) and delegates no reasoning; Solver reasons over the projection.

Mirrors :mod:`loomground_solver.adapters.loomground`; deontic is the second
language Solver consumes through the same adapter seam.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import deontic

from .models import (
    AdapterCapabilities, CoordinateAssignment, NDSystem, SolverProjection,
    SystemIdentity,
)

ADAPTER_ID = "solver.adapter.deontic"
ADAPTER_VERSION = "1"

# operator -> semantic role on its edge; the dimension comes from the deontic
# composition contract (dimension_affinity), not restated here.
SEMANTIC_ROLE = {"O": "obligates", "P": "permits", "F": "forbids"}


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class DeonticAdapter:
    """Project deontic statements without delegating reasoning."""

    def identity(self) -> SystemIdentity:
        return SystemIdentity(
            "loomground-deontic", deontic.language_version(),
            hashlib.sha256(deontic.grammar_text().encode("utf-8")).hexdigest(),
            ADAPTER_ID, ADAPTER_VERSION,
        )

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            artifacts=True, parsing=True, semantic_projection=True,
            evaluation=False, export=False,
        )

    def parse(self, source: str) -> list[dict]:
        """Parse one-or-more canonical statements (one per line) to projections."""
        return [deontic.project(deontic.parse(line))
                for line in source.splitlines() if line.strip()]

    def project(self, source) -> SolverProjection:
        statements = self.parse(source) if isinstance(source, str) else list(source)
        return self.import_observation({"statements": statements})

    def nd_system(self) -> NDSystem:
        axes = {
            "operator": {"type": "controlled", "values": list(deontic.VALID_OPERATORS)},
            "incident": {"type": "controlled", "values": list(deontic.INCIDENTS)},
            "negated": {"type": "controlled", "values": ["true", "false"]},
            "bearer": {"type": "reference", "open": True},
            "action": {"type": "reference", "open": True},
            "counterparty": {"type": "reference", "open": True},
            "condition": {"type": "reference", "open": True},
            "exception": {"type": "reference", "open": True},
        }
        version = f"{deontic.language_version()}+{deontic.CONTRACT_VERSION}"
        return NDSystem("loomground-deontic", "deontic", version, axes)

    def import_observation(self, observation: dict) -> SolverProjection:
        statements = observation.get("statements")
        if not isinstance(statements, list):
            raise ValueError("deontic observation requires a 'statements' list")
        system = self.nd_system()
        source_id = f"urn:deontic:grammar:{self.identity().artifact_sha256}"
        edges: list[dict] = []
        assignments: list[CoordinateAssignment] = []

        def assign(subject: str, axis: str, value: Any) -> None:
            if value in (None, ""):
                return
            assignments.append(CoordinateAssignment(
                f"nda:{_digest((subject, axis, value))[:16]}", subject,
                system.system_id, system.version, axis, value, source_id,
                f"{ADAPTER_ID}@{ADAPTER_VERSION}",
            ))

        for s in statements:
            op, bearer, action = s["operator"], s["bearer"], s["action"]
            if op not in deontic.VALID_OPERATORS or not bearer or not action:
                raise ValueError(f"deontic statement not well-formed: {s!r}")
            edges.append({
                "subject": bearer, "predicate": op, "object": action,
                "dimension": deontic.dimension_affinity(op),
                "semantic_role": SEMANTIC_ROLE.get(op, "governs"),
                "attributes": {k: s.get(k, "") for k in
                               ("condition", "exception", "negated", "incident", "counterparty")},
            })
            subject = f"norm:{_digest(s)[:16]}"
            assign(subject, "operator", op)
            assign(subject, "negated", "true" if s.get("negated") else "false")
            for axis in ("incident", "counterparty", "condition", "exception", "bearer", "action"):
                assign(subject, axis, s.get(axis))

        pair = {
            "id": f"deontic:{_digest(statements)[:16]}",
            "problem": {"id": "deontic-observation", "summary": "Deontic projection",
                        "facets": {}},
            "solution": {"id": "deontic-projection", "problem_id": "deontic-observation",
                         "body": "Canonical deontic semantic projection", "confidence": 1.0},
            "edges": edges,
        }
        return SolverProjection(
            self.identity(), (pair,), (system,), tuple(assignments), dict(observation)
        ).validate()


def adapt_deontic(source_or_statements) -> SolverProjection:
    """Convenience entry point for source text or a list of statement dicts."""
    return DeonticAdapter().project(source_or_statements)
