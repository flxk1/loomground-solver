# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Divergence: a trajectory compared against the purpose it was given.

The case that matters is the one no amount of reading the steps reveals — every
action locally defensible, the run as a whole serving something it was not
authorised to serve. These tests build exactly that and check it is found.

They also defend the boundary. The kernel contributes the comparison, never the
judgement: `serves` and `defeats` arrive already decided, and if this module ever
starts deriving them it has begun guessing at the thing it exists to make
checkable.
"""
from __future__ import annotations

from loomground_solver.cross_subsumption import Verdict
from loomground_solver.divergence import (
    KINDS, Divergence, Mandate, TrajectoryStep as S, detect, fold_divergences,
)

MANDATE = Mandate("doc#7:120-180", frozenset({"review", "draft"}))


def _clean_run():
    return [S("read the brief", serves=frozenset({"review"})),
            S("draft the note", serves=frozenset({"draft"}))]


# --- the case the steps do not reveal -------------------------------------------

def test_a_run_of_locally_reasonable_steps_can_still_diverge():
    run = _clean_run() + [S("place an order", serves=frozenset({"procure"}))]
    kinds = {d.kind for d in detect(MANDATE, run)}
    assert "out-of-mandate" in kinds


def test_the_letter_can_be_served_while_the_purpose_is_defeated():
    # Nominally serves `draft`, and works against `review`. Nothing about the
    # step in isolation looks wrong.
    run = _clean_run() + [
        S("delete the audit trail",
          serves=frozenset({"draft"}), defeats=frozenset({"review"}))]
    (d,) = [x for x in detect(MANDATE, run) if x.kind == "defeats-purpose"]
    assert d.ref == "delete the audit trail"
    assert "review" in d.why


def test_a_clean_run_reports_nothing():
    assert detect(MANDATE, _clean_run()) == ()


def test_a_purpose_no_step_served_is_reported():
    run = [S("read the brief", serves=frozenset({"review"}))]
    (d,) = [x for x in detect(MANDATE, run) if x.kind == "unserved"]
    assert d.ref == "draft"


# --- fail-closed on an absent mandate --------------------------------------------

def test_an_empty_mandate_authorises_nothing():
    # An actor given no purpose has been given nothing to pursue. Reading an
    # empty mandate as permission for everything would invert the rule.
    ds = detect(Mandate("doc#9", frozenset()), [S("anything")])
    assert [d.kind for d in ds] == ["out-of-mandate"]


def test_an_empty_run_leaves_every_declared_purpose_unserved():
    ds = detect(MANDATE, [])
    assert {d.ref for d in ds} == {"review", "draft"}
    assert {d.kind for d in ds} == {"unserved"}


# --- the three shapes stay distinct -----------------------------------------------

def test_findings_and_open_questions_map_differently():
    # A defeated purpose was compared and found wrong. An unserved one may just
    # mean the run is unfinished.
    found = fold_divergences([Divergence("defeats-purpose", "s", "w")])
    open_q = fold_divergences([Divergence("unserved", "p", "w")])
    assert found.overall is Verdict.NOT_SATISFIED
    assert open_q.overall is Verdict.OPEN


def test_an_open_question_dominates_a_finding():
    # "We do not yet know whether this purpose was served" must not be closed by
    # having found a different failure.
    out = fold_divergences([
        Divergence("defeats-purpose", "s", "w"),
        Divergence("unserved", "p", "w"),
    ])
    assert out.overall is Verdict.OPEN


def test_no_divergence_means_nothing_was_found_not_that_the_run_was_right():
    # Vacuous SATISFIED. The comparison is only as good as the judgements handed
    # in, and this test exists so that is not quietly forgotten.
    assert fold_divergences([]).overall is Verdict.SATISFIED


def test_ordering_is_stable_and_most_consequential_first():
    run = [S("a", serves=frozenset({"x"})),
           S("b", serves=frozenset({"draft"}), defeats=frozenset({"review"}))]
    kinds = [d.kind for d in detect(MANDATE, run)]
    assert kinds == sorted(kinds, key=KINDS.index)
    assert detect(MANDATE, run) == detect(MANDATE, run)


# --- the kernel compares; it does not judge -----------------------------------------

def test_serves_and_defeats_are_never_derived():
    # If this module ever infers which purpose an action served, it has started
    # making the guess it exists to make checkable.
    import inspect

    from loomground_solver import divergence as mod
    src = inspect.getsource(mod)
    for forbidden in ("def _infer", "def _classify", "def _guess", "re.compile"):
        assert forbidden not in src, forbidden


def test_purposes_are_opaque_to_the_kernel():
    # Any identifiers work — non-ASCII, punctuated, whatever the caller uses. The
    # kernel compares membership and reads none of them.
    m = Mandate("r", frozenset({"überprüfen", "x-9"}))
    served = [S("a", serves=frozenset({"überprüfen"})),
              S("b", serves=frozenset({"x-9"}))]
    assert detect(m, served) == ()
    # and an unmatched one is reported by the same membership comparison
    (d,) = detect(m, [S("a", serves=frozenset({"überprüfen"})),
                      S("b", serves=frozenset({"x-9"})),
                      S("c", serves=frozenset({"UBERPRUFEN"}))])
    assert d.kind == "out-of-mandate" and d.ref == "c"


def test_the_mandate_reference_travels_into_the_reason():
    # A reader must be able to go and check what was actually conferred.
    run = [S("s", serves=frozenset({"draft"}), defeats=frozenset({"review"}))]
    (d,) = [x for x in detect(MANDATE, run) if x.kind == "defeats-purpose"]
    assert MANDATE.ref in d.why


def test_output_plugs_into_the_oversight_brief():
    from loomground_solver import oversight_brief
    ds = detect(MANDATE, [S("place an order", serves=frozenset({"procure"}))])
    brief = oversight_brief(divergences=ds)
    assert brief.items[0].kind == "divergence"
    assert brief.items[0].why
