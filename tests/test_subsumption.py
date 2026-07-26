# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Subsumption + end-to-end rule reasoning: Tatbestand→facts, exceptions,
model-escalation via the judge port, forward chaining, and the full
extract-plug → subsume → apply → resolve pipeline."""
from __future__ import annotations

from loomground_solver import (
    Rule, subsume, applicable_rules, forward_chain, to_norms, solve_rules,
    LEX_CONFLICT_PACK, GENERIC_PACK,
)


def test_subsume_applicable_missing_and_exception():
    r = Rule("r1", conditions=("processing", "eu-nexus"), consequence="O:erase",
             exceptions=("legal-hold",))
    ok = subsume(r, {"processing", "eu-nexus"})
    assert ok.applicable and ok.missing == ()
    miss = subsume(r, {"processing"})
    assert not miss.applicable and miss.missing == ("eu-nexus",)
    blocked = subsume(r, {"processing", "eu-nexus", "legal-hold"})
    assert not blocked.applicable and blocked.blocked_by == ("legal-hold",)  # read to the end


def test_closed_world_default_and_judge_escalation():
    r = Rule("r", conditions=("open-textured",), consequence="q")
    assert not subsume(r, set()).applicable          # unproven ≠ true (closed world)
    # a judge (a model, verified) decides the open-textured condition
    judge = lambda lit, facts: lit == "open-textured"
    assert subsume(r, set(), judge=judge).applicable


def test_forward_chaining_descriptive_rules_to_fixpoint():
    rules = [Rule("a", ("data-collected",), "processing"),
             Rule("b", ("processing",), "controller-duties")]
    got = forward_chain(rules, {"data-collected"})
    assert {"processing", "controller-duties"} <= got


def test_to_norms_only_applicable_deontic_rules():
    rules = [Rule("n1", ("processing",), modality="obligatory", act="erase", source="s1"),
             Rule("n2", ("retention",), modality="prohibited", act="erase", source="s2")]
    norms = to_norms(rules, {"processing"})
    assert [n.act for n in norms] == ["erase"] and norms[0].deontic == "obligatory"


def test_solve_end_to_end_conflict_resolved_by_lex():
    rules = [
        Rule("mk-proc", ("data-collected",), "processing"),                 # descriptive
        Rule("gdpr17", ("processing",), modality="obligatory", act="erase",
             source="gdpr17", specificity=1),
        Rule("retention", ("retention-duty",), modality="prohibited", act="erase",
             source="hgb", specificity=3),
    ]
    facts = {"data-collected", "retention-duty"}
    res = solve_rules(rules, facts, pack=LEX_CONFLICT_PACK)
    r = res.resolution_for("erase")
    assert r.status == "determinate" and r.verdict == "prohibited"          # lex-specialis
    # generic pack cannot separate -> genuine collision escalates
    res2 = solve_rules(rules, facts, pack=GENERIC_PACK)
    assert res2.resolution_for("erase").status == "open"


def test_solve_exception_removes_a_conflicting_norm():
    rules = [
        Rule("gdpr17", ("processing",), modality="obligatory", act="erase", source="gdpr17"),
        Rule("retention", ("retention-duty",), modality="prohibited", act="erase",
             source="hgb", specificity=3, exceptions=("consent-withdrawn",)),
    ]
    # the retention norm is blocked by its own exception -> only the duty to erase stands
    res = solve_rules(rules, {"processing", "retention-duty", "consent-withdrawn"},
                      pack=LEX_CONFLICT_PACK)
    r = res.resolution_for("erase")
    assert r.status == "determinate" and r.verdict == "obligatory"
