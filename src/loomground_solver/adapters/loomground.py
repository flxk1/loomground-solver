"""Built-in Loomground reference adapter to Solver 5D+nD input."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from loomground_governance import grammar, language_version, vocabulary

from .. import loomground as runtime
from .models import (
    AdapterCapabilities, CoordinateAssignment, NDSystem, SolverProjection,
    SystemIdentity,
)

ADAPTER_ID = "solver.adapter.loomground"
ADAPTER_VERSION = "1"

RELATIONS = {
    "authority": ("intentional", "authorizes"),
    "pipe": ("causal", "activates"),
    "egress": ("causal", "releases_to"),
    "on_behalf_of": ("relational", "delegates_for"),
    "reservation": ("intentional", "reserves_for"),
    "redress": ("intentional", "remedy_by"),
}


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class LoomgroundAdapter:
    """Project canonical Loomground observations without delegating reasoning."""

    def identity(self) -> SystemIdentity:
        return SystemIdentity(
            "loomground-governance", language_version(),
            hashlib.sha256(grammar().encode("utf-8")).hexdigest(),
            ADAPTER_ID, ADAPTER_VERSION,
        )

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            artifacts=True, parsing=True, semantic_projection=True,
            evaluation=True, export=False,
        )

    def parse(self, source: str):
        return runtime.parse(source)

    def project(self, program) -> SolverProjection:
        patch = runtime.apply(program)
        return self.import_observation(runtime.project(patch))

    def nd_system(self) -> NDSystem:
        risk = list(vocabulary("risk")["levels"])
        grades = list(vocabulary("grades")["levels"])
        axes = {
            "node_class": {"type": "controlled", "values": ["actor", "human", "gate", "master"]},
            "cord_type": {"type": "controlled", "values": ["authority", "pipe", "egress"]},
            "risk": {"type": "ordered", "values": risk},
            "grade": {"type": "ordered", "values": grades},
            "party": {"type": "reference", "open": True},
            "token_kind": {"type": "reference", "open": True},
            "duration": {"type": "interval", "open": True},
            "on_elapse": {"type": "controlled", "values": ["halt", "proceed"]},
            "reservation_role": {"type": "reference", "open": True},
            "redress_role": {"type": "reference", "open": True},
        }
        version = f"{language_version()}+{_digest({'risk': risk, 'grades': grades, 'mapping': 1})[:12]}"
        return NDSystem("loomground-governance", "loomground", version, axes)

    def import_observation(self, observation: dict) -> SolverProjection:
        required = ("nodes", "cords", "reservations")
        if any(not isinstance(observation.get(field), list) for field in required):
            raise ValueError("Loomground observation requires nodes, cords, and reservations lists")
        system = self.nd_system()
        source_id = f"urn:loomground:grammar:{self.identity().artifact_sha256}"
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

        for node in observation["nodes"]:
            node_id, node_class = str(node.get("id", "")), str(node.get("class", ""))
            if not node_id or not node_class:
                raise ValueError("Loomground observation node requires id and class")
            assign(node_id, "node_class", node_class)
            for field, axis in (("risk_floor", "risk"), ("grade", "grade"),
                                ("grade_required", "grade"), ("party", "party")):
                assign(node_id, axis, node.get(field))
            if node.get("on_behalf_of"):
                edges.append(self._edge(node_id, "on_behalf_of", str(node["on_behalf_of"])))

        for cord in observation["cords"]:
            predicate = str(cord.get("type", ""))
            source, target = str(cord.get("from", "")), str(cord.get("to", ""))
            edges.append(self._edge(source, predicate, target, cord))
            assign(f"edge:{_digest((source, predicate, target))[:16]}", "cord_type", predicate)

        for reservation in observation["reservations"]:
            subject = f"reservation:{_digest(reservation)[:16]}"
            role = f"role:{reservation.get('by', '')}"
            edges.append(self._edge(subject, "reservation", role, reservation))
            for field, axis in (("kind", "token_kind"), ("by", "reservation_role"),
                                ("duration", "duration"), ("on_elapse", "on_elapse")):
                assign(subject, axis, reservation.get(field))

        for redress in observation.get("redress", []):
            subject = f"redress:{_digest(redress)[:16]}"
            role = f"role:{redress.get('by', '')}"
            edges.append(self._edge(subject, "redress", role, redress))
            assign(subject, "redress_role", redress.get("by"))
            assign(subject, "duration", redress.get("within"))

        pair = {
            "id": f"loomground:{_digest(observation)[:16]}",
            "problem": {"id": "loomground-observation", "summary": "Loomground projection",
                        "facets": {}},
            "solution": {"id": "loomground-projection", "problem_id": "loomground-observation",
                         "body": "Canonical Loomground semantic projection", "confidence": 1.0},
            "edges": edges,
        }
        return SolverProjection(
            self.identity(), (pair,), (system,), tuple(assignments), dict(observation)
        ).validate()

    @staticmethod
    def _edge(source: str, predicate: str, target: str,
              attributes: dict | None = None) -> dict:
        if predicate not in RELATIONS:
            raise ValueError(f"no Federation-5D mapping for {predicate!r}")
        if not source or not target:
            raise ValueError("Loomground relation requires source and target")
        dimension, semantic_role = RELATIONS[predicate]
        return {
            "subject": source, "predicate": predicate, "object": target,
            "dimension": dimension, "semantic_role": semantic_role,
            "attributes": dict(attributes or {}),
        }


def adapt_loomground(source_or_observation) -> SolverProjection:
    """Convenience entry point for source text, a patch, or an observation."""
    adapter = LoomgroundAdapter()
    if isinstance(source_or_observation, str):
        return adapter.project(source_or_observation)
    if isinstance(source_or_observation, dict) and all(
            key in source_or_observation for key in ("nodes", "cords", "reservations")):
        return adapter.import_observation(source_or_observation)
    return adapter.project(source_or_observation)
