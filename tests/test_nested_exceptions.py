# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Nested exceptions — Ausnahme / Rückausnahme trees (O58).

The polarity alternates with depth: a firing exception blocks the rule, a firing
counter-exception (Rückausnahme) un-blocks it, a firing counter-counter-exception
re-blocks it. The per-node truth check is consumed from :func:`subsumption.holds`
(closed-world default; optional ``judge`` escalation), never reimplemented.
"""
from __future__ import annotations

from loomground_solver.nested_exceptions import (
    ExceptionNode, ExceptionVerdict, NodeEval,
    evaluate_exceptions, blocks,
)


def test_no_exceptions_rule_not_blocked():
    v = evaluate_exceptions([], {"anything"})
    assert isinstance(v, ExceptionVerdict)
    assert v.blocked is False
    assert v.deciding_level == 0
    assert v.firing_chain == ()
    assert v.evaluations == ()
    assert blocks([], {"anything"}) is False


def test_single_exception_condition_holds_blocks():
    exc = ExceptionNode("legal-hold", label="hold")
    v = evaluate_exceptions([exc], {"legal-hold"})
    assert v.blocked is True
    assert v.deciding_level == 1
    assert v.firing_chain == ("hold",)
    assert blocks([exc], {"legal-hold"}) is True
    # the single top-level evaluation fired, with no defeaters
    (ev,) = v.evaluations
    assert isinstance(ev, NodeEval)
    assert ev.fired is True and ev.condition_holds is True
    assert ev.defeated_by == () and ev.level == 1


def test_single_exception_condition_absent_does_not_block():
    # closed-world via holds: an unproven condition does not hold
    exc = ExceptionNode("legal-hold", label="hold")
    v = evaluate_exceptions([exc], {"processing"})
    assert v.blocked is False
    assert v.deciding_level == 1
    assert v.firing_chain == ()
    (ev,) = v.evaluations
    assert ev.condition_holds is False and ev.fired is False


def test_firing_rueckausnahme_unblocks_a_firing_exception():
    # Regel with Ausnahme A (holds) and Rückausnahme R (holds): R fires, so A is
    # defeated, so A does not fire, so the rule is NOT blocked. [un-block case]
    R = ExceptionNode("consent-withdrawn", label="R")
    A = ExceptionNode("retention-duty", children=(R,), label="A")
    facts = {"retention-duty", "consent-withdrawn"}
    v = evaluate_exceptions([A], facts)
    assert v.blocked is False
    assert v.deciding_level == 2
    assert v.firing_chain == ("R",)          # only R fired along the decisive branch
    # A appears in evaluations, condition held but it was defeated by R
    (a_ev,) = v.evaluations
    assert a_ev.condition_holds is True
    assert a_ev.fired is False
    assert "R" in a_ev.defeated_by
    (r_ev,) = a_ev.children
    assert r_ev.fired is True and r_ev.level == 2


def test_rueckausnahme_condition_absent_leaves_exception_firing():
    # A holds, R present but R.condition not in facts: R does not fire, so A fires.
    R = ExceptionNode("consent-withdrawn", label="R")
    A = ExceptionNode("retention-duty", children=(R,), label="A")
    v = evaluate_exceptions([A], {"retention-duty"})
    assert v.blocked is True
    assert v.deciding_level == 2              # R was still consulted, one level down
    assert v.firing_chain == ("A",)
    (a_ev,) = v.evaluations
    assert a_ev.fired is True and a_ev.defeated_by == ()


def test_depth_three_alternation():
    # A holds / R holds / RR holds -> RR fires -> R defeated -> A not defeated -> A fires.
    RR = ExceptionNode("rr-cond", label="RR")
    R = ExceptionNode("r-cond", children=(RR,), label="R")
    A = ExceptionNode("a-cond", children=(R,), label="A")
    facts = {"a-cond", "r-cond", "rr-cond"}
    v = evaluate_exceptions([A], facts)
    assert v.blocked is True
    assert v.deciding_level == 3
    assert v.firing_chain == ("A", "RR")     # A fired, R defeated, RR fired
    (a_ev,) = v.evaluations
    assert a_ev.fired is True
    (r_ev,) = a_ev.children
    assert r_ev.fired is False and "RR" in r_ev.defeated_by
    (rr_ev,) = r_ev.children
    assert rr_ev.fired is True and rr_ev.level == 3


def test_judge_escalation_decides_open_textured_exception():
    # The exception condition is neither present nor negated in the facts.
    exc = ExceptionNode("manifestly-unreasonable", label="open")
    facts: set = set()
    # closed-world default: holds returns False, so the exception does not fire
    assert evaluate_exceptions([exc], facts).blocked is False
    assert blocks([exc], facts) is False
    # with a judge (a model, verified) that decides the open-textured literal true,
    # the exception fires and blocks — confirming holds is consumed, not reimplemented
    judge = lambda lit, f: lit == "manifestly-unreasonable"
    v = evaluate_exceptions([exc], facts, judge=judge)
    assert v.blocked is True
    assert v.firing_chain == ("open",)
    assert blocks([exc], facts, judge=judge) is True


# --- edge cases -----------------------------------------------------------

def test_negated_fact_keeps_closed_world_false():
    # an explicitly negated condition does not hold (holds sees neg present)
    exc = ExceptionNode("legal-hold", label="hold")
    v = evaluate_exceptions([exc], {"-legal-hold"})
    assert v.blocked is False and v.firing_chain == ()
    # even a judge is not consulted when the negation is present in the facts
    judge = lambda lit, f: True
    assert evaluate_exceptions([exc], {"-legal-hold"}, judge=judge).blocked is False


def test_multiple_top_level_exceptions_any_fires_blocks():
    e1 = ExceptionNode("cond-a", label="A")   # absent
    e2 = ExceptionNode("cond-b", label="B")   # present -> fires
    v = evaluate_exceptions([e1, e2], {"cond-b"})
    assert v.blocked is True
    assert v.firing_chain == ("B",)
    assert len(v.evaluations) == 2


def test_two_children_first_firing_child_defeats_parent():
    # two Rückausnahmen; only the second fires -> parent still defeated, no fire
    r1 = ExceptionNode("r1", label="R1")      # absent
    r2 = ExceptionNode("r2", label="R2")      # present -> fires, defeats A
    A = ExceptionNode("a", children=(r1, r2), label="A")
    v = evaluate_exceptions([A], {"a", "r2"})
    assert v.blocked is False
    assert v.firing_chain == ("R2",)
    (a_ev,) = v.evaluations
    assert a_ev.fired is False and a_ev.defeated_by == ("R2",)


def test_deciding_level_zero_only_when_forest_empty():
    exc = ExceptionNode("x", label="x")
    assert evaluate_exceptions([exc], set()).deciding_level == 1
    assert evaluate_exceptions([], set()).deciding_level == 0
