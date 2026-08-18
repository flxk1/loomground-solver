# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Proxies: what a measurement stands for, and whether anyone checked.

The load-bearing test is not the Goodhart case, which is easy once both readings
exist. It is that an *unchecked* proxy never reads as a healthy one, and that one
unchecked link makes a whole chain of substitutions unchecked however well every
other link tracked — the case an audit misses because each hop looks fine on its
own.
"""
from __future__ import annotations

import pytest

from loomground_solver.cross_subsumption import Verdict
from loomground_solver.proxy import (
    KINDS, Movement as M, Proxy as P, ProxyCycle,
    chain, check_proxies, fold_substitutions,
)

# The caller's vocabulary, not the kernel's — test data only.
SERVED = P("response_time", "client_was_served", ref="policy#3")


def _kinds(proxies, readings):
    return {s.metric: s.kind for s in check_proxies(proxies, readings)}


# --- the substitution comes apart -------------------------------------------------

def test_a_metric_improving_while_its_goal_worsens_is_a_finding():
    out = _kinds([SERVED], {"response_time": M.IMPROVED,
                            "client_was_served": M.WORSENED})
    assert out["response_time"] == "gamed"


def test_the_reason_names_both_sides_and_where_the_substitution_was_declared():
    (s,) = check_proxies([SERVED], {"response_time": M.IMPROVED,
                                    "client_was_served": M.WORSENED})
    assert "response_time" in s.why and "client_was_served" in s.why
    assert "policy#3" in s.why


def test_both_moving_together_is_the_substitution_holding_this_once():
    out = _kinds([SERVED], {"response_time": M.IMPROVED,
                            "client_was_served": M.IMPROVED})
    assert out["response_time"] == "tracking"


def test_the_instrument_can_be_what_is_in_question():
    # Metric down, goal up. Nothing is wrong with the run; the substitution is
    # what stops being usable.
    out = _kinds([SERVED], {"response_time": M.WORSENED,
                            "client_was_served": M.IMPROVED})
    assert out["response_time"] == "misleading"


# --- unchecked is the case that matters ---------------------------------------------

def test_an_unmeasured_goal_makes_the_reading_no_evidence():
    out = _kinds([SERVED], {"response_time": M.IMPROVED})
    assert out["response_time"] == "unchecked"


def test_nobody_looked_is_not_the_same_as_it_held_still():
    # If these ever coincide, an unchecked proxy is being recorded as a healthy
    # one, which is the whole failure this module exists to make visible.
    unchecked = _kinds([SERVED], {"response_time": M.IMPROVED})
    still = _kinds([SERVED], {"response_time": M.IMPROVED,
                              "client_was_served": M.UNCHANGED})
    assert unchecked["response_time"] != still["response_time"]


def test_an_absent_subject_reads_as_unmeasured_not_as_absent_of_concern():
    assert _kinds([SERVED], {}) == {"response_time": "unchecked"}


def test_an_explicit_unmeasured_and_an_omitted_reading_agree():
    a = _kinds([SERVED], {"response_time": M.IMPROVED})
    b = _kinds([SERVED], {"response_time": M.IMPROVED,
                          "client_was_served": M.UNMEASURED})
    assert a == b


def test_an_unmeasured_metric_is_also_unchecked():
    out = _kinds([SERVED], {"client_was_served": M.IMPROVED})
    assert out["response_time"] == "unchecked"


# --- the fold -------------------------------------------------------------------------

def test_a_gamed_substitution_is_a_finding_and_unchecked_is_an_open_question():
    gamed = fold_substitutions(check_proxies(
        [SERVED], {"response_time": M.IMPROVED, "client_was_served": M.WORSENED}))
    unchecked = fold_substitutions(check_proxies([SERVED], {"response_time": M.IMPROVED}))
    assert gamed.overall is Verdict.NOT_SATISFIED
    assert unchecked.overall is Verdict.OPEN


def test_one_unchecked_link_makes_the_whole_chain_unchecked():
    # Every other hop tracks. An audit that stops at the first hop sees nothing.
    hops = [P("a", "b"), P("b", "c"), P("c", "d")]
    readings = {"a": M.IMPROVED, "b": M.IMPROVED, "c": M.IMPROVED}  # d unmeasured
    out = fold_substitutions(check_proxies(hops, readings))
    assert out.overall is Verdict.OPEN
    failing = [n for n, v in out.issues if v is not Verdict.SATISFIED]
    assert failing == ["unchecked:c"]


def test_an_open_question_dominates_a_finding():
    # Repairing the gamed metric must not close a link nobody has measured.
    out = fold_substitutions(check_proxies(
        [P("a", "b"), P("c", "d")],
        {"a": M.IMPROVED, "b": M.WORSENED, "c": M.IMPROVED}))
    assert out.overall is Verdict.OPEN


def test_a_fully_tracking_chain_passes():
    hops = [P("a", "b"), P("b", "c")]
    out = fold_substitutions(check_proxies(
        hops, {"a": M.IMPROVED, "b": M.IMPROVED, "c": M.IMPROVED}))
    assert out.overall is Verdict.SATISFIED


def test_no_declared_substitution_means_none_was_declared():
    # Vacuous SATISFIED. Proxies nobody wrote down cannot be checked here, and
    # this test exists so that is not quietly read as "no proxies were used".
    assert fold_substitutions(()).overall is Verdict.SATISFIED


# --- chains must ground out --------------------------------------------------------------

def test_a_chain_is_followed_to_the_end():
    hops = [P("a", "b"), P("b", "c"), P("c", "d")]
    assert [p.stands_for for p in chain("a", hops)] == ["b", "c", "d"]


def test_a_metric_standing_for_nothing_declared_has_no_chain():
    assert chain("z", [P("a", "b")]) == ()


def test_a_self_referring_substitution_is_refused():
    with pytest.raises(ProxyCycle):
        chain("a", [P("a", "a")])


def test_a_cycle_is_refused_rather_than_truncated():
    # Returning the prefix would present "grounds in nothing" as "grounds weakly".
    with pytest.raises(ProxyCycle):
        chain("a", [P("a", "b"), P("b", "c"), P("c", "a")])


def test_the_refusal_says_what_it_found():
    with pytest.raises(ProxyCycle, match="grounds out"):
        chain("a", [P("a", "b"), P("b", "a")])


def test_a_chain_that_grounds_out_is_not_refused_for_re_entering_a_metric_name():
    # Diamond, not a cycle: two metrics standing for the same goal is ordinary.
    assert len(chain("a", [P("a", "c"), P("b", "c")])) == 1


# --- ordering and determinism ---------------------------------------------------------------

def test_most_consequential_first_and_stable():
    proxies = [P("t", "t2"), P("u", "u2"), P("g", "g2")]
    readings = {"t": M.IMPROVED, "t2": M.IMPROVED,
                "g": M.IMPROVED, "g2": M.WORSENED, "u": M.IMPROVED}
    out = check_proxies(proxies, readings)
    kinds = [s.kind for s in out]
    assert kinds == sorted(kinds, key=KINDS.index)
    assert out == check_proxies(proxies, readings)


# --- the kernel compares; it does not judge -------------------------------------------------

def test_movements_and_substitutions_are_never_derived():
    # Inferring that a metric "improved", or that one thing stands for another,
    # is exactly the judgement this layer exists to make checkable.
    import inspect

    from loomground_solver import proxy as mod
    src = inspect.getsource(mod)
    for forbidden in ("def _infer", "def _classify", "def _guess", "re.compile", ">="):
        assert forbidden not in src, forbidden


def test_subjects_are_opaque_to_the_kernel():
    out = _kinds([P("Durchsatz", "Mandant-zufrieden")],
                 {"Durchsatz": M.IMPROVED, "Mandant-zufrieden": M.WORSENED})
    assert out["Durchsatz"] == "gamed"


def test_movements_may_be_passed_as_plain_strings():
    # A caller reading readings out of JSON should not have to import the enum.
    out = _kinds([SERVED], {"response_time": "improved",
                            "client_was_served": "worsened"})
    assert out["response_time"] == "gamed"


def test_an_unknown_movement_is_refused_rather_than_guessed():
    with pytest.raises(ValueError):
        check_proxies([SERVED], {"response_time": "better-ish"})


def test_output_plugs_into_the_oversight_brief():
    from loomground_solver import oversight_brief
    subs = check_proxies([SERVED], {"response_time": M.IMPROVED,
                                    "client_was_served": M.WORSENED})
    brief = oversight_brief(divergences=subs)
    assert brief.items[0].why
