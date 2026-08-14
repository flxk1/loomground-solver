# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Reasoning contract — the governance-free core (loomground_solver.contract).

Ported from host tests/test_reasoning_contract.py, keeping ONLY the tests that
exercise the pure contract (check_case / required_oversight / check_export with
an injected classifier). The module-level imports of workspaces.problem_kg,
legal_corpus, decision_surface, rule_registry and policy are dropped; only
``loomground_solver.contract`` is imported. See the module docstring's SKIPPED
list for the tests intentionally left in the host shim layer.

SKIPPED (need a real corpus registry / folder policy — deferred to the shim):
  * test_build_case_enforces_the_contract  — needs registry + problem_kg.build_case
  * test_build_case_stake_blocks_auto_answer_below_floor — needs registry + decision_surface
  * test_check_folder_case_reads_the_policy — needs workspaces.policy + check_folder_case
"""

from __future__ import annotations

import pytest

from loomground_solver import contract as rc


def _case(**over) -> dict:
    base = {
        "problem": {"text": "q", "document": "d.md", "pinpoint": ""},
        "grounds": [{"pinpoint": "Art. 33(1)", "text": "notify", "entity": "gdpr",
                     "receipted": True}],
        "chain": [], "gaps": [], "facts": [], "actions": [],
        "resolution": {"type": "determinate", "answer": "72h"},
        "coverage": 1.0, "profile": "legal-de",
    }
    base.update(over)
    return base


# ── R1 evidence ───────────────────────────────────────────────────────────────

def test_r1_unevidenced_fact_is_a_violation():
    rep = rc.check_case(_case(facts=[{"text": "customer requested erasure", "source": ""}]))
    assert any(f.code == "RC-1" for f in rep.violations)
    rep2 = rc.check_case(_case(facts=[{"text": "…", "source": "ticket #4711"}]))
    assert rep2.ok


def test_r1_hidden_gap_is_a_violation():
    rep = rc.check_case(_case(gaps=["Art. 34"], coverage=1.0))
    assert any(f.code == "RC-1" for f in rep.violations)


# ── R2 warrants ───────────────────────────────────────────────────────────────

def test_r2_unwarranted_step_escalates_never_hides():
    rep = rc.check_case(_case(chain=[{"step": "Subsumtion", "text": "applies"}]))
    assert rep.ok and any(f.code == "RC-2" for f in rep.escalations)
    rep2 = rc.check_case(_case(chain=[{"step": "Subsumtion", "text": "applies",
                                       "warrant": "Art. 33(1) wording 'shall notify'"}]))
    assert not any(f.code == "RC-2" for f in rep2.escalations)


# ── R3 resolution ─────────────────────────────────────────────────────────────

def test_r3_rubber_stamp_and_fake_options_are_violations():
    res = {"type": "residual",
           "surface": {"options": [{"id": "a"}, {"id": "b"}]},
           "choice": {"chosen_option_id": "a", "rationale": "", "actor": "operator"}}
    assert any(f.code == "RC-3" for f in rc.check_case(_case(resolution=res)).violations)
    res2 = {"type": "residual", "surface": {"options": [{"id": "only"}]}, "choice": None}
    assert any(f.code == "RC-3" for f in rc.check_case(_case(resolution=res2)).violations)


# ── R4 judgment floor (Oversight alignment) ──────────────────────────────────

def test_r4_esc_and_stake_require_approve_floor():
    open_case = _case(resolution={"type": "open", "note": ""})
    rep = rc.check_case(open_case, oversight_level="review", stake=True)
    assert any(f.code == "RC-4" for f in rep.violations)
    rep2 = rc.check_case(open_case, oversight_level="approve", stake=True)
    assert not any(f.code == "RC-4" for f in rep2.violations)


def test_r4_personal_forbids_auto_answer_and_requires_manual():
    rep = rc.check_case(_case(), oversight_level="manual", personal=True)
    assert any("auto-emitted" in f.message for f in rep.violations)   # determinate auto-answer
    chosen = _case(resolution={"type": "residual",
                               "surface": {"options": [{"id": "a"}, {"id": "b"}]},
                               "choice": {"chosen_option_id": "a",
                                          "rationale": "because", "actor": "operator"}})
    assert rc.check_case(chosen, oversight_level="manual", personal=True).ok
    assert not rc.check_case(chosen, oversight_level="approve", personal=True).ok


def test_r4_oversight_disabled_drops_to_autonomous():
    open_case = _case(resolution={"type": "open", "note": ""})
    rep = rc.check_case(open_case, oversight_level="approve",
                        oversight_active=False, stake=True)
    assert any(f.code == "RC-4" and "disabled" in f.message for f in rep.violations)


def test_required_oversight_is_the_manifest_floor():
    assert rc.required_oversight(esc=True, stake=True, personal=False) == "approve"
    assert rc.required_oversight(esc=False, stake=False, personal=True) == "manual"
    assert rc.required_oversight(esc=True, stake=False, personal=False) == "autonomous"


# ── R5 actions ────────────────────────────────────────────────────────────────

def test_r5_no_action_from_an_open_case_and_actions_cite_their_norm():
    a = [{"obligation": "notify authority", "actor": "controller",
          "deadline": "72h", "source_norm": "Art. 33(1)"}]
    assert rc.check_case(_case(actions=a)).ok
    open_case = _case(resolution={"type": "open", "note": ""}, actions=a)
    assert any(f.code == "RC-5" for f in rc.check_case(open_case).violations)
    unanchored = _case(actions=[{"obligation": "do something", "source_norm": ""}])
    assert any(f.code == "RC-5" for f in rc.check_case(unanchored).violations)


# ── profiles are data ─────────────────────────────────────────────────────────

def test_profiles_render_vocabulary_not_logic():
    irac = _case(profile="legal-irac",
                 chain=[{"step": "Issue", "text": "t", "warrant": "w"},
                        {"step": "Rule", "text": "t", "warrant": "w"}])
    assert not any(f.code == "RC-7" for f in rc.check_case(irac).escalations)
    wrong = _case(profile="legal-irac",
                  chain=[{"step": "Tatbestand", "text": "t", "warrant": "w"}])
    assert any(f.code == "RC-7" for f in rc.check_case(wrong).escalations)
    assert any(f.code == "RC-7" for f in rc.check_case(_case(profile="nope")).escalations)


# ── Workspace Lock alignment (R6 custody at the boundary) — injected classifier ──

def test_r6_export_requires_classification_then_acknowledgement():
    case = _case(facts=[{"text": "Max Mustermann, Berliner Str. 1", "source": "contract"}])
    # no classifier injected → custody unknown → escalate
    assert rc.check_export([case]).must_escalate
    hot = lambda t: {"findings": 1 if "Mustermann" in t else 0}
    rep = rc.check_export([case], classify=hot)
    assert any(f.code == "RC-6" for f in rep.escalations)
    rep2 = rc.check_export([case], classify=hot, acknowledged=True)
    assert rep2.ok and not rep2.must_escalate
    clean = lambda t: {"findings": 0}
    assert not rc.check_export([case], classify=clean).must_escalate


# ── RC-8: read the norm to the end ────────────────────────────────────────────

_EXC_GROUND = {"pinpoint": "Art. 33(1)", "text": "…", "entity": "gdpr",
               "receipted": True, "condition": "a personal data breach",
               "consequence": "notify the supervisory authority",
               "exception": "the personal data breach is unlikely to result in "
                            "a risk to the rights and freedoms of natural persons"}


def test_rc8_unexamined_exception_blocks_auto_closure():
    case = _case(grounds=[dict(_EXC_GROUND)],
                 chain=[{"step": "Norm", "text": "duty to notify",
                         "warrant": "Art. 33(1) wording", "canon": "verbatim"}])
    rep = rc.check_case(case)
    assert any(f.code == "RC-8" for f in rep.escalations)
    assert "not read to the end" in next(f for f in rep.escalations
                                         if f.code == "RC-8").message


def test_rc8_examined_exception_passes():
    case = _case(grounds=[dict(_EXC_GROUND)],
                 chain=[{"step": "Norm", "text": "duty to notify",
                         "warrant": "Art. 33(1) wording", "canon": "verbatim"},
                        {"step": "Ausnahme",
                         "text": "Is the breach unlikely to result in a risk "
                                 "to the rights and freedoms of natural persons?",
                         "warrant": "Art. 33(1) 'unless' clause", "canon": "verbatim"}])
    rep = rc.check_case(case)
    assert not any(f.code == "RC-8" for f in rep.escalations)


def test_rc8_open_case_carries_no_rc8_noise():
    case = _case(grounds=[dict(_EXC_GROUND)],
                 resolution={"type": "open", "note": ""})
    assert not any(f.code == "RC-8"
                   for f in rc.check_case(case).escalations)
