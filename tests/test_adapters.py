# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Versum adapter + governance-injection tests. The Versum NormSource lets the KG
drive the solver; the governance test uses a plain fake Governance (no host tool),
so it stays a pure test of the core contract's judgment floor. host-specific
adapter tests live in the host repo's loomground-solver-integration/, not here."""
from __future__ import annotations

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from loomground_solver.ports import NormSource, Governance, NullGovernance
from loomground_solver import api
from loomground_solver import Norm, Scenario, derive, GENERIC_PACK
from loomground_solver.adapters import VersumNormSource


def _write_claims(tmp_path):
    d = tmp_path / ".versum"
    d.mkdir()
    p = d / "claims.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["canonical_urn", "source_urn", "text",
                                           "polarity", "predicate", "modality"])
        w.writeheader()
        w.writerow({"canonical_urn": "urn:dls:celex:32016R0679", "source_urn": "urn:dls:source:gdpr",
                    "text": "The controller shall erase.", "polarity": "D",
                    "predicate": "imposes", "modality": "obliged"})
        w.writerow({"canonical_urn": "", "source_urn": "urn:kg:source:note1",
                    "text": "A definition.", "polarity": "D",
                    "predicate": "defines", "modality": "definitional"})
    return tmp_path


def test_versum_normsource_maps_claims_keyed_by_canonical_urn(tmp_path):
    folder = _write_claims(tmp_path)
    src = VersumNormSource(folder)
    assert isinstance(src, NormSource)
    spans = src.norm_spans_for(set())
    assert len(spans) == 2
    s0 = spans[0]
    assert s0["pinpoint"] == "urn:dls:celex:32016R0679"
    assert s0["anchors"][0]["entity"] == "celex"
    # default modality_map: Versum's "obliged" now bridges to the solver's
    # "obligatory" (rulepacks.CONTRADICTIONS), not an identity pass-through.
    assert s0["modal"] == "obligatory"
    assert s0["condition"] == "" and s0["consequence"] == "" and s0["exception"] == ""
    assert src.held_pinpoints() == {"urn:dls:celex:32016R0679", "urn:kg:source:note1"}
    assert [s["pinpoint"] for s in src.norm_spans_for({"celex"})] == ["urn:dls:celex:32016R0679"]
    # "definitional" is explicitly non-deontic: no modal, never a guessed Norm.
    assert spans[1]["modal"] == ""


def test_versum_normsource_accepts_host_modality_vocabulary(tmp_path):
    source = VersumNormSource(_write_claims(tmp_path), modality_map={"obliged": "shall"})
    assert source.norm_spans_for(set())[0]["modal"] == "shall"


def test_versum_default_modality_map_yields_deontic_collision(tmp_path):
    """S1: an obliged claim and a prohibited claim on the same act must yield a
    genuine collision once the adapter's default modality_map bridges Versum's
    vocabulary onto the solver's (rulepacks.CONTRADICTIONS)."""
    root = tmp_path / ".versum"
    root.mkdir()
    with open(root / "claims.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=(
            "canonical_urn", "source_urn", "text", "polarity", "predicate",
            "modality"))
        writer.writeheader()
        writer.writerow({
            "canonical_urn": "urn:dls:celex:a", "source_urn": "urn:dls:source:a",
            "text": "The controller shall share the data.", "polarity": "D",
            "predicate": "imposes", "modality": "obliged"})
        writer.writerow({
            "canonical_urn": "urn:dls:celex:b", "source_urn": "urn:dls:source:b",
            "text": "The controller shall not share the data.", "polarity": "D",
            "predicate": "imposes", "modality": "prohibited"})
    spans = VersumNormSource(root).norm_spans_for(set())
    assert [s["modal"] for s in spans] == ["obligatory", "prohibited"]
    norms = [Norm("share-data", span["modal"], source=span["pinpoint"]) for span in spans]
    resolution = derive(Scenario("w", norms=norms), pack=GENERIC_PACK).resolution_for("share-data")
    assert resolution.status == "open" and resolution.verdict is None
    assert ("urn:dls:celex:a", "urn:dls:celex:b") in [
        tuple(sorted(c)) for c in resolution.collisions
    ]


def test_versum_normsource_rejects_unmapped_modality(tmp_path):
    """An unmapped Versum modality must never pass through silently onto
    Norm.deontic — it is a vocabulary gap and fails loudly."""
    root = tmp_path / ".versum"
    root.mkdir()
    with open(root / "claims.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=(
            "canonical_urn", "source_urn", "text", "polarity", "predicate",
            "modality"))
        writer.writeheader()
        writer.writerow({
            "canonical_urn": "urn:dls:celex:x", "source_urn": "urn:dls:source:x",
            "text": "Something unmapped.", "polarity": "D", "predicate": "imposes",
            # not a value any shipped profile or real store emits — a genuine
            # vocabulary gap, not one of the recognised non-deontic labels.
            "modality": "mystery-modal"})
    src = VersumNormSource(root)
    with pytest.raises(ValueError, match="unmapped Versum modality"):
        src.norm_spans_for(set())


def test_versum_normsource_preserves_grounded_deontic_composition(tmp_path):
    root = tmp_path / ".versum"
    root.mkdir()
    with open(root / "claims.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=(
            "item_id", "canonical_urn", "source_urn", "text", "polarity",
            "predicate", "modality"))
        writer.writeheader()
        writer.writerow({
            "item_id": "claim:1", "canonical_urn": "urn:dls:celex:rule1",
            "source_urn": "urn:dls:source:policy", "text": "Controller must erase.",
            "polarity": "N", "predicate": "imposes", "modality": "obliged",
        })
    composition = {
        "composition_id": "cmp:rule:1", "kind": "deontic",
        "participants": [
            {"role": "bearer", "target_id": "controller", "evidence_ids": ["claim:1"]},
            {"role": "action", "target_id": "erase", "evidence_ids": ["claim:1"]},
            {"role": "condition", "target_id": "request-valid", "evidence_ids": ["claim:1"]},
            {"role": "exception", "target_id": "legal-hold", "evidence_ids": ["claim:1"]},
        ],
        # a REAL native Versum modality (not a made-up label): this exercises
        # the deontic composition's nd_scope.modal override path through the
        # same mapping/raise-on-unmapped as row.get("modality") (S1 round 2).
        "nd_scope": {"modal": "prohibited", "jurisdiction": ["eu"]},
    }
    (root / "compositions.jsonl").write_text(
        json.dumps(composition) + "\n", encoding="utf-8")
    nd_root = root / "nd"
    nd_root.mkdir()
    with open(nd_root / "assignments.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=(
            "assignment_id", "subject_id", "system_id", "system_version",
            "axis_id", "value", "source_id", "method", "confidence",
            "verification"))
        writer.writeheader()
        writer.writerow({
            "assignment_id": "nda:1", "subject_id": "claim:1",
            "system_id": "rule-nd", "system_version": "1",
            "axis_id": "jurisdiction", "value": json.dumps(["eu"]),
            "source_id": "claim:1", "method": "rule-nd@1",
            "confidence": "1", "verification": "verified",
        })
    with open(nd_root / "bindings.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=(
            "binding_id", "claim_id", "form_slot", "semantic_role",
            "assignment_id", "axis_id", "value", "source_id", "method",
            "confidence", "verification"))
        writer.writeheader()
        writer.writerow({
            "binding_id": "ndb:1", "claim_id": "claim:1",
            "form_slot": "scope", "semantic_role": "applies_in",
            "assignment_id": "nda:1", "axis_id": "jurisdiction",
            "value": json.dumps(["eu"]), "source_id": "claim:1",
            "method": "rule-nd@1", "confidence": "1",
            "verification": "verified",
        })

    span = VersumNormSource(tmp_path).norm_spans_for(set())[0]
    assert span["bearer"] == "controller"
    assert span["consequence"] == "erase"
    assert span["condition"] == "request-valid"
    assert span["exception"] == "legal-hold"
    assert span["modal"] == "prohibited"  # mapped (prohibited -> prohibited), not raw
    assert span["composition_ids"] == ["cmp:rule:1"]
    assert span["nd_scope"] == [{"modal": "prohibited", "jurisdiction": ["eu"]}]
    assert span["compositions"] == [composition]
    assert span["nd_assignments"][0]["value"] == ["eu"]
    assert span["nd_bindings"][0]["assignment_id"] == "nda:1"


def test_versum_normsource_rejects_unmapped_modality_via_nd_scope(tmp_path):
    """S1 round 2: the deontic composition's own ``nd_scope.modal`` override is a
    SECOND path onto ``Norm.deontic`` — a raw or unmapped value reaching it
    through this path, bypassing the row's own ``modality`` column entirely,
    must fail exactly like an unmapped ``row.get("modality")`` does."""
    root = tmp_path / ".versum"
    root.mkdir()
    with open(root / "claims.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=(
            "item_id", "canonical_urn", "source_urn", "text", "polarity",
            "predicate", "modality"))
        writer.writeheader()
        writer.writerow({
            "item_id": "claim:1", "canonical_urn": "urn:dls:celex:rule2",
            "source_urn": "urn:dls:source:policy2", "text": "Controller must erase.",
            # the ROW's own modality is a recognised, mapped value — the point of
            # this test is that the OVERRIDE below is checked independently.
            "polarity": "N", "predicate": "imposes", "modality": "obliged",
        })
    composition = {
        "composition_id": "cmp:rule:2", "kind": "deontic",
        "participants": [
            {"role": "bearer", "target_id": "controller", "evidence_ids": ["claim:1"]},
        ],
        "nd_scope": {"modal": "mystery-modal"},
    }
    (root / "compositions.jsonl").write_text(
        json.dumps(composition) + "\n", encoding="utf-8")
    src = VersumNormSource(root)
    with pytest.raises(ValueError, match="unmapped Versum modality"):
        src.norm_spans_for(set())


# The distinct `modality` values a read-only scan (2026-10-11) of the four real
# Versum stores under ~/work/loomground-data/ (music-rights, legal-first-aid,
# digital-law, trademark) actually carries — a fixture, not a live filesystem
# read, so this test stays hermetic and portable across machines/CI. S1 round 2
# (addendum): the shipped default map must cover all of it without raising.
REAL_STORE_MODALITY_VALUES = frozenset({
    "", "definitional", "exempt", "null", "obligatory", "obliged", "permitted",
    "prohibited", "void", "interrogative",
})


def test_default_modality_map_covers_every_value_in_the_real_stores(tmp_path):
    source = VersumNormSource(tmp_path)  # default modality_map, no override
    for value in REAL_STORE_MODALITY_VALUES:
        source._modal(value)  # must not raise for any real-store value


def test_default_modality_map_maps_the_literal_string_null_to_non_deontic(tmp_path):
    source = VersumNormSource(tmp_path)
    assert source._modal("null") == ""


class _FakeGov:
    def __init__(self, level="approve", active=True):
        self._level, self._active = level, active
    def oversight_level(self): return self._level
    def oversight_active(self): return self._active
    def classify(self, text): return {"findings": 0}
    def record(self, event): return None


def _esc_stake_case():
    return {
        "problem": {"text": "Q"},
        "facts": [{"text": "f", "source": "doc"}],
        "grounds": [{"pinpoint": "X", "receipted": True}],
        "chain": [{"step": "rule", "warrant": "w"}],
        "gaps": [], "coverage": 1.0,
        "resolution": {"type": "residual", "surface": {"options": [{"id": "a"}, {"id": "b"}]}},
        "profile": "generic",
    }


def _codes(report):
    return [(f.code, f.level.value) for f in report.findings]


def test_governance_injection_moves_the_judgment_floor():
    case = _esc_stake_case()
    gov = _FakeGov("approve", True)
    assert isinstance(gov, Governance)
    rep_null = api.check(case, governance=NullGovernance(), stake=True)
    assert any(c == "RC-4" and lvl == "violation" for c, lvl in _codes(rep_null))
    rep_ok = api.check(case, governance=gov, stake=True)
    assert not any(c == "RC-4" and lvl == "violation" for c, lvl in _codes(rep_ok))
    assert any(c == "RC-4" and lvl == "escalate" for c, lvl in _codes(rep_ok))


def test_normsource_grounds_flow_into_reasoning(tmp_path):
    src = VersumNormSource(_write_claims(tmp_path))
    spans = src.norm_spans_for(set())
    pairs = [
        {"id": spans[0]["pinpoint"], "edges": [
            {"subject": "controller", "predicate": "imposes",
             "object": "erasure-duty", "dimension": "causal"}]},
        {"id": "e2", "edges": [
            {"subject": "erasure-duty", "predicate": "enables",
             "object": "data-subject-right", "dimension": "causal"}]},
    ]
    infs = api.entail(pairs, subject="controller", max_hops=3)
    assert any(i.object == "data-subject-right" for i in infs)
