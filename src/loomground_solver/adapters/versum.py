# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Read Versum's native claim semantics through Solver's corpus port.

The adapter consumes persisted Versum claims, typed compositions and nD
coordinates without importing Versum into Solver core. It retains the native
records on each projected norm span while exposing the deontic fields used by
Solver's existing case builder.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


CLAIM_AXES_SCHEMA = "loomground.versum.claim-axes/v1"

#: The five recognized axes, in canonical order. Any other key is out of bounds.
CLAIM_AXES = ("predicate", "modality", "polarity", "quantification", "domain")

_MAX_AXIS_VALUE_LEN = 256


#: Closed per-axis decision sets for profile version 0.1.0 — exactly the inert
#: choices this profile supports. Richer semantics (typed relations, deontic
#: operators, scope behavior, retrieval selection) arrive as new profile
#: versions with their own closed sets, never by widening these. "attack" is
#: permanently outside polarity's set: a negative polarity is annotation, never
#: an auto-minted attack relation.
_PROFILE_CHOICES = {
    "predicate": frozenset({"descriptive"}),
    "modality": frozenset({"inert"}),
    "polarity": frozenset({"annotation"}),
    "quantification": frozenset({"inert"}),
    "domain": frozenset({"inert"}),
}


@dataclass(frozen=True)
class ClaimAxesProfile:
    """Versioned semantic profile for the claim-axes schema.

    Stage 2 of the two-stage adapter: one explicit decision per axis, validated
    against the closed sets above at construction — the profile is a declaration
    attached to inert output, not a semantic compiler, and an unrecognized
    decision is an error, never a silently serialized claim.

    Polarity is constrained to non-attack readings: it may (in some future
    version) map to negation or annotation, never to an auto-minted attack
    relation.
    """

    profile_id: str = "loomground.versum.claim-axes.inert"
    version: str = "0.1.0"
    predicate: str = "descriptive"
    modality: str = "inert"
    polarity: str = "annotation"
    quantification: str = "inert"
    domain: str = "inert"

    def __post_init__(self):
        if not self.profile_id.strip() or not self.version.strip():
            raise ValueError("profile_id and version are required")
        for axis, allowed in _PROFILE_CHOICES.items():
            value = getattr(self, axis)
            if value not in allowed:
                raise ValueError(
                    f"unsupported {axis} decision {value!r}; "
                    f"this profile version allows {sorted(allowed)}")

    def to_dict(self) -> dict:
        return {"profile_id": self.profile_id, "version": self.version,
                "axes": {axis: getattr(self, axis) for axis in CLAIM_AXES}}


class ClaimAxesDecoder:
    """Stage 1 of the two-stage Versum adapter: bounds-checked decoding only.

    Recognized axes are preserved verbatim as candidate metadata; the decoder
    invents no edges, no attacks, and no logical consequences — in particular a
    negative polarity never becomes an attack. Anything outside the declared
    bounds (unknown axis, unknown top-level key, non-string or oversized value)
    is rejected fail-closed.
    """

    def __init__(self, profile: ClaimAxesProfile | None = None):
        if profile is not None and not isinstance(profile, ClaimAxesProfile):
            raise TypeError("profile must be a ClaimAxesProfile")
        self.profile = profile or ClaimAxesProfile()

    def supports(self, schema: str) -> bool:
        return schema == CLAIM_AXES_SCHEMA

    def compile(self, candidate) -> dict:
        data = dict(candidate.structural_evidence or {})
        schema = str(data.get("schema", ""))
        if not self.supports(schema):
            raise ValueError(f"unsupported structural schema: {schema}")
        unknown_keys = set(data) - {"schema", "axes"}
        if unknown_keys:
            raise ValueError(
                f"claim-axes evidence has unknown keys: {sorted(unknown_keys)}")
        if "axes" not in data:
            # A conforming producer always emits the key; its absence signals
            # malformed or version-skewed output, not "no axes".
            raise ValueError("claim-axes evidence must carry an axes object")
        axes = data["axes"]
        if not isinstance(axes, dict):
            raise ValueError("claim axes must be an object")
        unknown_axes = set(axes) - set(CLAIM_AXES)
        if unknown_axes:
            raise ValueError(f"unknown claim axes: {sorted(unknown_axes)}")
        clean = {}
        for axis in CLAIM_AXES:
            if axis not in axes:
                continue
            value = axes[axis]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"claim axis {axis!r} must be a non-empty string")
            if len(value) > _MAX_AXIS_VALUE_LEN:
                raise ValueError(f"claim axis {axis!r} exceeds "
                                 f"{_MAX_AXIS_VALUE_LEN} characters")
            clean[axis] = value
        pair = {
            "id": candidate.candidate_id,
            "problem": {"id": f"{candidate.candidate_id}:problem",
                        "summary": candidate.claim,
                        "facets": {"claim_axes": clean,
                                   "semantic_profile": self.profile.to_dict()}},
            "solution": {"id": candidate.candidate_id,
                         "problem_id": f"{candidate.candidate_id}:problem",
                         "body": candidate.claim, "confidence": 1.0},
            "edges": [],
        }
        return {"pairs": [pair], "attacks": [], "schema": CLAIM_AXES_SCHEMA}


class VersumNormSource:
    """Implement ``NormSource`` over one persisted Versum knowledge folder."""

    def __init__(
        self,
        versum_folder,
        *,
        claims_csv=None,
        compositions_jsonl=None,
        assignments_csv=None,
        bindings_csv=None,
        modality_map=None,
    ):
        base = Path(versum_folder)
        root = base if base.name == ".versum" else base / ".versum"
        self._claims = Path(claims_csv) if claims_csv else root / "claims.csv"
        self._compositions = (
            Path(compositions_jsonl)
            if compositions_jsonl
            else root / "compositions.jsonl"
        )
        self._assignments = (
            Path(assignments_csv)
            if assignments_csv
            else root / "nd" / "assignments.csv"
        )
        self._bindings = (
            Path(bindings_csv) if bindings_csv else root / "nd" / "bindings.csv"
        )
        self._modality_map = dict(modality_map or {})

    @staticmethod
    def _csv_rows(path: Path, *, json_value: bool = False) -> list[dict]:
        if not path.is_file():
            return []
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if json_value:
            for line_number, row in enumerate(rows, 2):
                try:
                    row["value"] = json.loads(row.get("value", "null"))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid Versum nD value at {path}:{line_number}: {exc}"
                    ) from exc
        return rows

    def _rows(self) -> list[dict]:
        return self._csv_rows(self._claims)

    def _composition_rows(self) -> list[dict]:
        if not self._compositions.is_file():
            return []
        rows = []
        for line_number, line in enumerate(
            self._compositions.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid Versum composition at line {line_number}: {exc}"
                ) from exc
            if not isinstance(row, dict):
                raise ValueError(
                    f"invalid Versum composition at line {line_number}: not an object"
                )
            rows.append(row)
        return rows

    @staticmethod
    def _index(rows: list[dict], key: str) -> dict[str, list[dict]]:
        indexed: dict[str, list[dict]] = {}
        for row in rows:
            identity = str(row.get(key) or "")
            if identity:
                indexed.setdefault(identity, []).append(row)
        return indexed

    def _compositions_by_claim(self) -> dict[str, list[dict]]:
        indexed: dict[str, list[dict]] = {}
        for composition in self._composition_rows():
            evidence = {
                str(evidence_id)
                for participant in composition.get("participants", ())
                if isinstance(participant, dict)
                for evidence_id in participant.get("evidence_ids", ())
            }
            for claim_id in evidence:
                indexed.setdefault(claim_id, []).append(composition)
        return indexed

    @staticmethod
    def _participant(composition: dict, role: str) -> str:
        for participant in composition.get("participants", ()):
            if not isinstance(participant, dict):
                continue
            if str(participant.get("role", "")).split(":", 1)[0] == role:
                return str(participant.get("target_id", ""))
        return ""

    @staticmethod
    def _entity_of(urn: str) -> str:
        parts = urn.split(":")
        return parts[-2] if len(parts) >= 2 else urn

    def _to_span(
        self,
        row: dict,
        compositions: list[dict] = (),
        assignments: list[dict] = (),
        bindings: list[dict] = (),
    ) -> dict:
        urn = (row.get("canonical_urn") or row.get("source_urn") or "").strip()
        span = {
            "kind": "norm",
            "pinpoint": urn,
            "text": row.get("text", ""),
            "anchors": [
                {
                    "entity": self._entity_of(urn),
                    "type": "instrument",
                    "relation": "cites",
                    "basis": urn,
                }
            ],
            "modal": self._modal(row.get("modality")),
            "condition": "",
            "consequence": "",
            "exception": "",
            "polarity": row.get("polarity", ""),
            "predicate": row.get("predicate", ""),
            "source_urn": row.get("source_urn", ""),
        }
        scopes = []
        for composition in compositions:
            scope = dict(composition.get("nd_scope") or {})
            scopes.append(scope)
            kind = composition.get("kind")
            if kind == "deontic":
                span["bearer"] = scope.get("bearer") or self._participant(
                    composition, "bearer"
                )
                span["consequence"] = scope.get("action") or self._participant(
                    composition, "action"
                )
                span["condition"] = scope.get("condition") or self._participant(
                    composition, "condition"
                )
                span["exception"] = scope.get("exception") or self._participant(
                    composition, "exception"
                )
                span["modal"] = scope.get("modal") or span["modal"]
            elif kind == "conditional":
                span["condition"] = scope.get("condition") or self._participant(
                    composition, "antecedent"
                )
                span["consequence"] = scope.get("consequence") or self._participant(
                    composition, "consequent"
                )
        if compositions:
            span["compositions"] = compositions
            span["composition_ids"] = [
                str(composition.get("composition_id", ""))
                for composition in compositions
            ]
            span["nd_scope"] = scopes
        if assignments:
            span["nd_assignments"] = assignments
        if bindings:
            span["nd_bindings"] = bindings
        return span

    def _modal(self, value) -> str:
        native = str(value or "").strip()
        return str(self._modality_map.get(native, native))

    def _native_indexes(self):
        return (
            self._compositions_by_claim(),
            self._index(self._csv_rows(self._assignments, json_value=True), "subject_id"),
            self._index(self._csv_rows(self._bindings, json_value=True), "claim_id"),
        )

    def norm_spans_for(self, instrument_codes: set) -> list[dict]:
        """Return Solver norm spans while retaining their native Versum semantics."""
        compositions, assignments, bindings = self._native_indexes()
        spans = []
        for row in self._rows():
            if not (row.get("text") or "").strip():
                continue
            claim_id = str(row.get("item_id") or "")
            span = self._to_span(
                row,
                compositions.get(claim_id, ()),
                assignments.get(claim_id, ()),
                bindings.get(claim_id, ()),
            )
            if not instrument_codes or any(
                anchor["entity"] in instrument_codes for anchor in span["anchors"]
            ):
                spans.append(span)
        return spans

    def held_pinpoints(self) -> set:
        """Return canonical URNs, falling back to source URNs when necessary."""
        return {
            (row.get("canonical_urn") or row.get("source_urn") or "").strip()
            for row in self._rows()
            if (row.get("text") or "").strip()
        }
