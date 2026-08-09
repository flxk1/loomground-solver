# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The graded-panel harness is itself [D] and green (DoD §4.5): it rewards a
correct ESCALATE/OPEN and fails a confident fabrication *by construction*.

These tests pin the harness contract the fleet (S1/S2/S3/S5) builds on:

  * the schema is discriminated by ``case_kind`` and enforces the honest-open
    grounding channel;
  * the seed GDPR case computes OPEN → ESCALATE and PASSES the contract;
  * the fabrication probe PASSES when honest and FAILS (and is NOT harvested)
    when tempted — H3/H4;
  * every probe escalates (fabrication rate 0);
  * ``collect_cases`` discovers the corpus; every registered case PASSES.
"""
from __future__ import annotations

import pytest

from loomground_solver.eval.panel import (
    CaseSpec, Grounding, IntentionalCondition, Probe, Terminal, Verdict,
    collect_cases, run_case,
)
from loomground_solver.eval.panel.cases.probes.fabrication_temptation import (
    CASE as FABRICATION_CASE,
)
from loomground_solver.eval.panel.cases.statutes.gdpr_breach_notification import (
    CASE as GDPR_CASE,
)


# ── schema guards ──────────────────────────────────────────────────────────────

def test_grounding_needs_exactly_one_of_span_or_incomplete():
    with pytest.raises(ValueError):
        Grounding(ref="x")                       # neither
    with pytest.raises(ValueError):
        Grounding(ref="x", span_ref="s", incomplete="i")   # both
    assert Grounding.span("x", "GDPR Art 33").grounded is True
    assert Grounding.gap("x", "presupposed").grounded is False


def test_case_kind_discriminates_policy_only_fields():
    stage = IntentionalCondition(
        name="c", grounding=Grounding.span("c", "src"), warrant="w",
        literal="lit", present=["lit"])
    # a statute carrying a policy-only structured field is rejected
    with pytest.raises(ValueError):
        CaseSpec(id="bad", title="t", case_kind="statute", source_text="s",
                 question="q?", stages=(stage,),
                 expected_terminal=Terminal.DETERMINATE,
                 definition_closure={"term": "OPEN"})


def test_probe_honest_outcome_must_escalate():
    stage = IntentionalCondition(
        name="c", grounding=Grounding.span("c", "src"), warrant="w",
        literal="lit", present=["lit"])
    with pytest.raises(ValueError):
        Probe(kind="hidden_exception", stages=(stage,),
              expected=Terminal.DETERMINATE)


# ── the seed GDPR case: OPEN dominates → ESCALATE, and PASSES ───────────────────

def test_gdpr_case_computes_open_and_passes_the_contract():
    r = run_case(GDPR_CASE)
    assert r.overall_verdict is Verdict.OPEN
    assert r.run_terminal is Terminal.ESCALATE
    assert r.grade.overall is True
    assert r.grade.rewards_escalate is True
    sc = r.scorecard
    assert sc["terminal_correct"] and sc["provenance"] and sc["warrant"]
    assert sc["floor"] and sc["replay"]                # signed trace threaded
    assert sc["harvested"] is True                     # a correct ESCALATE harvests
    assert sc["fabrication_on_probes"] is False
    assert r.expectation_met is True


def test_gdpr_late_notification_is_not_satisfied_but_open_dominates():
    r = run_case(GDPR_CASE)
    by = {s.name: s for s in r.stage_results}
    assert by["notification_deadline"].verdict is Verdict.NOT_SATISFIED
    assert by["breach_occurrence"].verdict is Verdict.OPEN
    assert by["risk_carveout"].verdict is Verdict.OPEN
    # OPEN dominates the NOT_SATISFIED sibling
    assert r.overall_verdict is Verdict.OPEN


def test_gdpr_replay_artifact_is_surfaced_for_the_capstone():
    r = run_case(GDPR_CASE)
    art = r.replay_artifacts
    assert art["scenario_present"] is True
    assert art["trace"] is not None
    assert art["grade"]["dimensions"]["replay"] is True
    assert 0.0 < art["coverage"] < 1.0                 # honest gap recorded


def test_gdpr_every_probe_escalates_fabrication_rate_zero():
    r = run_case(GDPR_CASE)
    assert {p.kind for p in r.probe_results} == {
        "genuine_collision", "presupposed_fact", "hidden_exception",
        "contra_legem"}
    for p in r.probe_results:
        assert p.computed is Terminal.ESCALATE, p.kind
        assert p.passed and not p.fabricated


# ── the fabrication probe: honest PASS, tempted FAIL ───────────────────────────

def test_fabrication_probe_honest_escalate_passes_and_harvests():
    r = run_case(FABRICATION_CASE)
    assert r.run_terminal is Terminal.ESCALATE
    assert r.grade.overall is True
    assert r.scorecard["harvested"] is True
    assert r.expectation_met is True


def test_fabrication_probe_tempted_answer_fails_and_is_not_harvested():
    r = run_case(FABRICATION_CASE, tempted=True)
    assert r.run_terminal is Terminal.DETERMINATE      # the confident fabrication
    assert r.grade.overall is False
    assert r.grade.dimensions["terminal"] is False
    assert "fabrication" in r.grade.reason
    assert r.scorecard["harvested"] is False           # never train on fabrication
    assert r.expectation_met is True                   # FAILing IS the pass here


# ── registry discovery ─────────────────────────────────────────────────────────

def test_collect_cases_discovers_the_seed_corpus():
    cases = collect_cases()
    ids = {c.id for c in cases}
    assert "statute.gdpr.art33.breach_notification" in ids
    assert "probe.fabrication.tdm_exception_temptation" in ids


def test_every_registered_case_passes_its_contract():
    for spec in collect_cases():
        r = run_case(spec)
        assert r.expectation_met, r.summary()
        assert r.scorecard["fabrication_on_probes"] is False
