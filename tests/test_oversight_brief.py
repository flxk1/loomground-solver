# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The oversight brief: bounded by what went unresolved, not by how much was done.

The load-bearing test here is `test_brief_size_does_not_grow_with_step_count`. It
is written to be able to FAIL: if the brief ever grows with the length of a
derivation, the scalability claim is false and this test says so, rather than
being adjusted until it passes.

The rest defend the other half — that this module SELECTS and never DECIDES. It
reads what the fold, the decision space and the fingerprint already determined. A
brief that minted a status or resolved an option would be a second opinion.
"""
from __future__ import annotations

from loomground_solver.decision import DecisionSpace
from loomground_solver.epistemic_status import EpistemicStatus as E
from loomground_solver.epistemic_status import StatusedPremise as S
from loomground_solver.oversight import KIND_ORDER, oversight_brief


def _chain(n: int, root: E = E.PRESUPPOSED):
    """One unsettled assumption, then `n` steps each inferred from the last."""
    out = [S("assumption", root)]
    for i in range(n):
        out.append(S(f"step-{i}", E.INFERRED,
                     depends_on=((f"step-{i-1}",) if i else ("assumption",))))
    return out


# --- the claim ----------------------------------------------------------------

def test_brief_size_does_not_grow_with_step_count():
    # THE claim. Fifty consequences of one assumption are one item, not fifty.
    sizes = {n: len(oversight_brief(premises=_chain(n))) for n in (10, 100, 1000)}
    assert set(sizes.values()) == {1}, f"brief grew with step count: {sizes}"


def test_the_consequences_are_carried_not_listed():
    # They are not discarded either — a reader can still see the blast radius.
    brief = oversight_brief(premises=_chain(50))
    (item,) = brief.items
    assert item.ref == "assumption"
    assert len(item.explains) == 50


def test_a_clean_run_yields_an_empty_brief():
    brief = oversight_brief(premises=_chain(500, root=E.ASSERTED))
    assert brief.empty
    assert brief.settled_omitted == 501


def test_settled_count_distinguishes_nothing_checked_from_all_clear():
    # An empty brief is ambiguous without it, and those are different situations.
    assert oversight_brief().settled_omitted == 0
    assert oversight_brief(premises=[S("a", E.ASSERTED)]).settled_omitted == 1


def test_every_unsettled_status_reaches_the_brief_with_a_reason():
    for status in (E.PRESUPPOSED, E.CONTESTED, E.UNKNOWN):
        (item,) = oversight_brief(premises=[S("p", status)]).items
        assert item.kind == "root-presupposition"
        assert item.why, f"{status} produced an item with no reason"


# --- ordering ------------------------------------------------------------------

def test_items_are_ordered_most_consequential_first():
    brief = oversight_brief(
        premises=_chain(3),
        space=DecisionSpace(accepted=[], undecided=["opt"], rejected=[], attacks=[]),
        negative_space={"unfired_defeaters": ["d"], "gaps": ["g"]},
        divergences=[("traj", "did not serve its purpose")],
    )
    kinds = [i.kind for i in brief.items]
    assert kinds == sorted(kinds, key=KIND_ORDER.index)
    assert kinds[0] == "divergence"


def test_divergence_leads_because_steps_will_not_reveal_it():
    brief = oversight_brief(
        premises=_chain(5),
        divergences=[("traj", "bought from an unapproved supplier")])
    assert brief.items[0].kind == "divergence"


# --- it selects; it does not decide --------------------------------------------

def test_nothing_is_invented_for_an_absent_source():
    assert oversight_brief().empty
    assert oversight_brief(negative_space={}).empty
    assert oversight_brief(space=DecisionSpace([], [], [], [])).empty


def test_an_accepted_option_never_appears():
    brief = oversight_brief(
        space=DecisionSpace(accepted=["safe"], undecided=[], rejected=[], attacks=[]))
    assert brief.empty
    assert brief.settled_omitted == 1


def test_a_rejected_option_never_appears():
    # Rejected is decided. Only the genuinely open set needs a supervisor.
    brief = oversight_brief(space=DecisionSpace(
        accepted=[], undecided=[], rejected=[{"id": "bad", "reason": "defeated"}],
        attacks=[]))
    assert brief.empty


def test_the_brief_mints_no_verdict_or_status():
    brief = oversight_brief(premises=_chain(3),
                            space=DecisionSpace([], ["x"], [], []))
    blob = str(brief.to_dict()).lower()
    for forbidden in ("satisfied", "not_satisfied", "verdict", "accepted", "pass"):
        assert forbidden not in blob, forbidden


def test_the_brief_does_not_mutate_its_inputs():
    premises = _chain(5)
    before = [(p.name, p.status, p.depends_on) for p in premises]
    oversight_brief(premises=premises)
    assert [(p.name, p.status, p.depends_on) for p in premises] == before


# --- honest edges ---------------------------------------------------------------

def test_a_dependency_cycle_becomes_a_gap_rather_than_a_fabricated_root():
    brief = oversight_brief(premises=[
        S("x", E.INFERRED, depends_on=("y",)),
        S("y", E.INFERRED, depends_on=("x",)),
    ])
    assert {i.ref for i in brief.of_kind("gap")} == {"x", "y"}
    assert not brief.of_kind("root-presupposition")


def test_a_dangling_dependency_is_surfaced_not_dropped():
    brief = oversight_brief(premises=[S("a", E.INFERRED, depends_on=("ghost",))])
    (gap,) = brief.of_kind("gap")
    assert "ghost" in gap.why


def test_negative_space_reaches_the_brief():
    brief = oversight_brief(negative_space={
        "unfired_defeaters": ["lex-posterior"],
        "untriggered_exceptions": ["unless notified"],
        "gaps": ["no authority for step 3"],
    })
    assert {i.kind for i in brief.items} == {
        "unfired-defeater", "untriggered-exception", "gap"}


def test_every_item_says_why_not_merely_that():
    brief = oversight_brief(
        premises=_chain(2),
        space=DecisionSpace([], ["x"], [], []),
        negative_space={"gaps": ["g"]},
        divergences=[("t", "")])
    for item in brief.items:
        assert item.why.strip(), f"{item.kind}/{item.ref} gives no reason"
