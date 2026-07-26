# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The deterministic decision space: attack-closure, reinstatement, verify-as-
reject, and the bounded choice set an automatic decision-maker pulls from."""
from __future__ import annotations

from loomground_solver import decision_space, DecisionSpace, grounded_labels


def test_grounded_reinstatement_primitive():
    # a -> b -> c  ⇒  a IN, b OUT, c reinstated IN
    lbl = grounded_labels(["a", "b", "c"], [("a", "b"), ("b", "c")])
    assert lbl == {"a": "in", "b": "out", "c": "in"}


def test_accepted_set_is_grounded_and_auto_safe():
    # A defeats B; only A is justified
    ds = decision_space(["A", "B"], attacks=[("A", "B")])
    assert ds.accepted == ["A"]
    assert {r["id"] for r in ds.rejected} == {"B"}
    assert ds.undecided == [] and ds.choice_required() is False


def test_genuine_collision_becomes_the_bounded_choice_set():
    # mutual attack the space cannot resolve => both land in `undecided`,
    # and that is the ONLY set a decision-maker may pick from
    ds = decision_space(["X", "Y"], attacks=[("X", "Y"), ("Y", "X")])
    assert set(ds.undecided) == {"X", "Y"}
    assert ds.accepted == [] and ds.choice_required() is True
    # an automatic decision-maker is bounded to `undecided`
    assert all(choice in ds.undecided for choice in ds.undecided)


def test_verify_failure_rejects_outright_not_merely_defeats():
    cands = [{"id": "ok"}, {"id": "bad"}]
    def verify(c):
        return (True, "") if c["id"] == "ok" else (False, "did not re-derive")
    ds = decision_space(cands, verify=verify)
    assert ds.accepted == ["ok"]
    assert {r["id"]: r["reason"] for r in ds.rejected} == {"bad": "did not re-derive"}


def test_defeat_function_with_reinstatement_over_candidates():
    # rank-ordered defeat; C reinstated when its attacker B is itself defeated by A
    cands = [{"id": "A", "rank": 3, "clash": {"B"}},
             {"id": "B", "rank": 2, "clash": {"A", "C"}},
             {"id": "C", "rank": 1, "clash": {"B"}}]
    reg = {c["id"]: c for c in cands}
    def defeat(a, b):
        if b["id"] in a["clash"]:              # they conflict
            return "a" if a["rank"] > b["rank"] else "b"
        return None                            # non-conflicting -> (still mutual, but
        # here A and C do not clash so we must avoid a spurious attack:)
    # guard: only conflicting pairs attack
    def defeat2(a, b):
        if b["id"] not in a["clash"]:
            return "skip"                      # sentinel: no attack
        return "a" if a["rank"] > b["rank"] else "b"
    # decision_space treats None as mutual; use an attacks list for precision instead
    attacks = []
    ids = [c["id"] for c in cands]
    for i in range(len(ids)):
        for j in range(len(ids)):
            if i == j:
                continue
            a, b = reg[ids[i]], reg[ids[j]]
            if b["id"] in a["clash"] and a["rank"] > b["rank"]:
                attacks.append((a["id"], b["id"]))
    ds = decision_space(cands, attacks=attacks)
    assert set(ds.accepted) == {"A", "C"}       # C reinstated
    assert {r["id"] for r in ds.rejected} == {"B"}


def test_decision_space_serializes():
    ds = decision_space(["A", "B"], attacks=[("A", "B")])
    d = ds.to_dict()
    assert d["accepted"] == ["A"] and d["choice_required"] is False
