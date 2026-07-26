import pytest

from loomground_solver import METHODS, method, methods_by_kind, reason_loomground
from loomground_solver.loomground import ApplyError, apply, parse, project


AUTO = """\
actor bot grade L3
gate decide risk low grade L2 grant bot
cord bot -> decide
cord decide -> master
"""

HUMAN = AUTO.replace("grade L3", "grade L1").replace("grade L2", "grade L3")


def transport(token_id="t1"):
    return {"activations": [{
        "actor": "bot", "source": "decide",
        "token": {"id": token_id, "kind": "act", "risk": "low",
                  "party": "deployer", "provenance": []},
    }]}


def test_loomground_is_a_registered_nd_route():
    assert "loomground" in METHODS
    assert "loomground" in methods_by_kind("route")
    assert method("loomground") is not None


def test_auto_release_maps_to_accepted_with_language_trace():
    result = reason_loomground(AUTO, transport())
    assert result["accepted"] == ["t1"]
    assert result["undecided"] == []
    assert result["trace"]["evaluation"]["decide"]["master"] == "act"
    assert result["trace"]["log"] == [{"gate": "decide", "verdict": "auto"}]


def test_human_withhold_maps_to_bounded_undecided():
    result = method("loomground")(HUMAN, transport())
    assert result["status"] == "escalate"
    assert result["undecided"] == ["t1"]
    assert result["accepted"] == []


def test_prohibition_and_release_keep_distinct_action_results():
    source = """\
actor a
gate g1 risk high grant a
gate g2 risk high grant a
prohibit deploy when tags contains untrusted_model
cord a -> g1
cord a -> g2
cord g1 -> master
cord g2 -> master
"""
    run = {"activations": [
        {"actor": "a", "source": "g1", "token": {
            "id": "blocked", "kind": "deploy", "risk": "high",
            "party": "provider", "provenance": [], "tags": ["untrusted_model"]}},
        {"actor": "a", "source": "g2", "token": {
            "id": "allowed", "kind": "deploy", "risk": "high",
            "party": "provider", "provenance": [], "tags": ["vetted"]}},
    ]}
    result = reason_loomground(source, run)
    assert result["accepted"] == ["allowed"]
    assert result["rejected"] == {"blocked": "prohibited"}


def test_apply_fails_closed_and_observation_is_canonical():
    with pytest.raises(ApplyError, match="cycle"):
        apply("gate a\ngate b\ncord a -> b\ncord b -> a\n")
    patch = apply(AUTO)
    assert project(patch) == project(parse(AUTO))
