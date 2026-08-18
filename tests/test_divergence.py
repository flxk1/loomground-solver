# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Divergence: a trajectory compared against the purpose it was given.

The case that matters is the one no amount of reading the steps reveals — every
action locally defensible, the run as a whole serving something it was not
authorised to serve. These tests build exactly that and check it is found.

They also defend two boundaries. The kernel contributes the comparison, never the
judgement: `serves` and `defeats` arrive already decided, and if this module ever
starts deriving them it has begun guessing at the thing it exists to make
checkable. And **both terms must be grounded** — a mandate or a step whose
reference does not verify produces a report about the record, never a finding
about the run. A finding resting on an unresolved reference is an assertion
wearing the costume of a check.
"""
from __future__ import annotations

import pytest

from loomground_solver.cross_subsumption import Verdict
from loomground_solver.divergence import (
    KINDS, Divergence, Mandate, TrajectoryStep as _S, detect, fold_divergences,
)
from loomground_solver.interop import EvidenceRef


def _ref(source: str, start: int = 0, end: int = 10) -> EvidenceRef:
    return EvidenceRef(source_id=source, span_start=start, span_end=end)


class Store:
    """The host's knowledge store, standing in for the engine one layer down.

    Verifies exactly the references it was told about; everything else fails, as
    an unresolvable reference should.
    """

    def __init__(self, *known):
        self._known = set(known)

    def resolve(self, ref):
        if ref.source_id not in self._known:
            raise KeyError(ref.source_id)
        return {"source_id": ref.source_id}

    def verify(self, ref):
        return ref.source_id in self._known


class Broken:
    """A store that cannot answer. Not confirming is not the same as confirming."""

    def resolve(self, ref):
        raise RuntimeError("store unavailable")

    def verify(self, ref):
        raise RuntimeError("store unavailable")


MANDATE = Mandate(_ref("engagement-letter", 120, 180),
                  frozenset({"review", "draft"}))
GROUND = Store("engagement-letter", "log")


def S(name, serves=frozenset(), defeats=frozenset(), source="log"):
    return _S(name, _ref(source), serves=serves, defeats=defeats)


def _clean_run():
    return [S("read the brief", serves=frozenset({"review"})),
            S("draft the note", serves=frozenset({"draft"}))]


def _detect(mandate, steps, store=GROUND):
    return detect(mandate, steps, evidence=store)


# --- the case the steps do not reveal -------------------------------------------

def test_a_run_of_locally_reasonable_steps_can_still_diverge():
    run = _clean_run() + [S("place an order", serves=frozenset({"procure"}))]
    assert "out-of-mandate" in {d.kind for d in _detect(MANDATE, run)}


def test_the_letter_can_be_served_while_the_purpose_is_defeated():
    # Nominally serves `draft`, and works against `review`. Nothing about the
    # step in isolation looks wrong.
    run = _clean_run() + [
        S("delete the audit trail",
          serves=frozenset({"draft"}), defeats=frozenset({"review"}))]
    (d,) = [x for x in _detect(MANDATE, run) if x.kind == "defeats-purpose"]
    assert d.ref == "delete the audit trail"
    assert "review" in d.why


def test_a_clean_run_reports_nothing():
    assert _detect(MANDATE, _clean_run()) == ()


def test_a_purpose_no_step_served_is_reported():
    run = [S("read the brief", serves=frozenset({"review"}))]
    (d,) = [x for x in _detect(MANDATE, run) if x.kind == "unserved"]
    assert d.ref == "draft"


# --- both terms must be grounded ---------------------------------------------------

def test_a_mandate_cannot_be_stated_without_saying_where_it_came_from():
    # No default. A purpose nobody can look up is the assertion this module
    # exists to refuse.
    with pytest.raises(TypeError):
        Mandate(purposes=frozenset({"review"}))


def test_an_unverifiable_mandate_stops_the_comparison():
    # It is the second term of every comparison here. Findings against a frame
    # nobody can check would read as authoritative and would not be.
    ds = _detect(MANDATE, _clean_run(), Store("log"))
    assert [d.kind for d in ds] == ["ungrounded"]
    assert "no checkable purpose" in ds[0].why


def test_an_unverifiable_step_costs_only_itself():
    run = _clean_run() + [S("phantom step", serves=frozenset({"review"}),
                            source="nowhere")]
    ds = _detect(MANDATE, run)
    assert [d.kind for d in ds] == ["ungrounded"]
    assert ds[0].ref == "phantom step"


def test_an_unverified_step_is_dropped_from_what_the_run_served():
    # Otherwise an unresolvable record could discharge a declared purpose, which
    # is the fail-open direction.
    run = [S("read the brief", serves=frozenset({"review"})),
           S("claimed draft", serves=frozenset({"draft"}), source="nowhere")]
    kinds = {(d.kind, d.ref) for d in _detect(MANDATE, run)}
    assert ("ungrounded", "claimed draft") in kinds
    assert ("unserved", "draft") in kinds


def test_the_citation_travels_into_the_reason():
    # A reader must be able to go and check the record, not take it on trust.
    run = [S("s", serves=frozenset({"draft"}), defeats=frozenset({"review"}))]
    (d,) = [x for x in _detect(MANDATE, run) if x.kind == "defeats-purpose"]
    assert "engagement-letter:120-180" in d.why


def test_a_store_that_cannot_answer_has_not_confirmed_anything():
    # Reading an exception as a pass would put the fail-open case exactly where
    # it does most damage.
    ds = _detect(MANDATE, _clean_run(), Broken())
    assert [d.kind for d in ds] == ["ungrounded"]


def test_verification_is_required_not_defaulted():
    # A caller who wants findings without checking must write the provider that
    # says yes, and thereby say so.
    with pytest.raises(TypeError):
        detect(MANDATE, _clean_run())


def test_the_knowledge_store_is_reached_through_the_port_not_imported():
    # The substrate that anchors claims to spans lives one layer down. This
    # module must consume it through the injected seam, never as a dependency.
    import inspect

    from loomground_solver import divergence as mod
    src = inspect.getsource(mod)
    assert "versum" not in src.lower()
    assert "from .ports import EvidenceProvider" in src


# --- fail-closed on an absent mandate --------------------------------------------

def test_an_empty_mandate_authorises_nothing():
    # An actor given no purpose has been given nothing to pursue. Reading an
    # empty mandate as permission for everything would invert the rule.
    ds = _detect(Mandate(_ref("engagement-letter"), frozenset()), [S("anything")])
    assert [d.kind for d in ds] == ["out-of-mandate"]


def test_an_empty_run_leaves_every_declared_purpose_unserved():
    ds = _detect(MANDATE, [])
    assert {d.ref for d in ds} == {"review", "draft"}
    assert {d.kind for d in ds} == {"unserved"}


# --- the shapes stay distinct -----------------------------------------------------

def test_findings_and_open_questions_map_differently():
    # A defeated purpose was compared and found wrong. An unserved one may just
    # mean the run is unfinished; an ungrounded one says nothing about conduct.
    found = fold_divergences([Divergence("defeats-purpose", "s", "w")])
    open_q = fold_divergences([Divergence("unserved", "p", "w")])
    unchecked = fold_divergences([Divergence("ungrounded", "p", "w")])
    assert found.overall is Verdict.NOT_SATISFIED
    assert open_q.overall is Verdict.OPEN
    assert unchecked.overall is Verdict.OPEN


def test_an_open_question_dominates_a_finding():
    # "We do not yet know" must not be closed by having found a different failure.
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
           S("b", serves=frozenset({"draft"}), defeats=frozenset({"review"})),
           S("c", serves=frozenset({"review"}), source="nowhere")]
    kinds = [d.kind for d in _detect(MANDATE, run)]
    assert kinds == sorted(kinds, key=KINDS.index)
    assert _detect(MANDATE, run) == _detect(MANDATE, run)


def test_ungrounded_leads_because_it_qualifies_everything_below_it():
    assert KINDS[0] == "ungrounded"


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
    m = Mandate(_ref("engagement-letter"), frozenset({"überprüfen", "x-9"}))
    served = [S("a", serves=frozenset({"überprüfen"})),
              S("b", serves=frozenset({"x-9"}))]
    assert _detect(m, served) == ()
    (d,) = _detect(m, served + [S("c", serves=frozenset({"UBERPRUFEN"}))])
    assert d.kind == "out-of-mandate" and d.ref == "c"


def test_output_plugs_into_the_oversight_brief():
    from loomground_solver import oversight_brief
    ds = _detect(MANDATE, [S("place an order", serves=frozenset({"procure"}))])
    brief = oversight_brief(divergences=ds)
    assert brief.items[0].kind == "divergence"
    assert brief.items[0].why
