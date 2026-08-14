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

from loomground_solver.ports import NormSource, Governance, NullGovernance
from loomground_solver import api
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
    assert s0["modal"] == "obliged"
    assert s0["condition"] == "" and s0["consequence"] == "" and s0["exception"] == ""
    assert src.held_pinpoints() == {"urn:dls:celex:32016R0679", "urn:kg:source:note1"}
    assert [s["pinpoint"] for s in src.norm_spans_for({"celex"})] == ["urn:dls:celex:32016R0679"]


def test_versum_normsource_accepts_host_modality_vocabulary(tmp_path):
    source = VersumNormSource(_write_claims(tmp_path), modality_map={"obliged": "shall"})
    assert source.norm_spans_for(set())[0]["modal"] == "shall"


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
        "nd_scope": {"modal": "prohibition", "jurisdiction": ["eu"]},
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
    assert span["modal"] == "prohibition"
    assert span["composition_ids"] == ["cmp:rule:1"]
    assert span["nd_scope"] == [{"modal": "prohibition", "jurisdiction": ["eu"]}]
    assert span["compositions"] == [composition]
    assert span["nd_assignments"][0]["value"] == ["eu"]
    assert span["nd_bindings"][0]["assignment_id"] == "nda:1"


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
