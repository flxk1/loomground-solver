import pytest

from loomground_solver import METHODS, method, methods_by_kind, reason_loomground
from loomground_solver.loomground import ApplyError, apply, parse, project
from loomground_solver.prom001 import GovernedRiskTable


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


FANOUT = """\
actor a
gate src risk low grant a
gate b risk high grant a
gate c risk low grant a
reserve act by safety when risk >= high
cord a -> src
cord src -> b
cord src -> c
cord b -> master
cord c -> master
"""

FANOUT_BOTH_ACT = FANOUT.replace("reserve act by safety when risk >= high\n", "") \
    .replace("gate b risk high grant a", "gate b risk low grant a")

FANOUT_ONE_REFUSED = FANOUT.replace("reserve act by safety when risk >= high\n", "") \
    .replace("gate b risk high grant a", "gate b risk low")


def fanout_transport(token_id="t1"):
    return {"activations": [{
        "actor": "a", "source": "src",
        "token": {"id": token_id, "kind": "act", "risk": "low",
                  "party": "deployer", "provenance": []},
    }]}


def test_fanout_one_reserved_terminal_is_undecided():
    result = reason_loomground(FANOUT, fanout_transport())
    assert result["accepted"] == []
    assert result["undecided"] == ["t1"]
    assert result["rejected"] == {}
    assert result["trace"]["evaluation"]["b"] == {"verdict": "reserved", "master": "withhold"}
    assert result["trace"]["evaluation"]["c"] == {"verdict": "auto", "master": "act"}


def test_fanout_every_terminal_acting_is_accepted():
    result = reason_loomground(FANOUT_BOTH_ACT, fanout_transport())
    assert result["accepted"] == ["t1"]
    assert result["undecided"] == []
    assert result["rejected"] == {}


def test_fanout_one_refused_terminal_is_rejected_refused():
    result = reason_loomground(FANOUT_ONE_REFUSED, fanout_transport())
    assert result["accepted"] == []
    assert result["undecided"] == []
    assert result["rejected"] == {"t1": "refused"}


def test_invalid_token_is_rejected_with_reason_invalid():
    transport = fanout_transport()
    transport["activations"][0]["token"]["risk"] = "not-a-risk-level"
    result = reason_loomground(FANOUT_BOTH_ACT, transport)
    assert result["accepted"] == []
    assert result["undecided"] == []
    assert result["rejected"] == {"t1": "invalid"}


SINGLE_RESERVED = """\
actor bot
gate decide risk high grant bot
reserve act by safety when risk >= high
cord bot -> decide
cord decide -> master
"""

SINGLE_REFUSED = """\
actor bot
gate src risk low grant bot
gate decide risk low
cord bot -> src
cord src -> decide
cord decide -> master
"""


def single_refused_transport(token_id="t1"):
    return {"activations": [{
        "actor": "bot", "source": "src",
        "token": {"id": token_id, "kind": "act", "risk": "low",
                  "party": "deployer", "provenance": []},
    }]}


def test_single_path_reserved_verdict_is_still_undecided():
    result = reason_loomground(SINGLE_RESERVED, transport())
    assert result["accepted"] == []
    assert result["undecided"] == ["t1"]
    assert result["rejected"] == {}


def test_single_path_refused_verdict_is_still_rejected():
    result = reason_loomground(SINGLE_REFUSED, single_refused_transport())
    assert result["accepted"] == []
    assert result["undecided"] == []
    assert result["rejected"] == {"t1": "refused"}


def test_non_dict_token_is_rejected_invalid_not_a_crash():
    run = {"activations": [
        {"actor": "a", "source": "src", "token": "junk"},
    ]}
    result = reason_loomground(FANOUT_BOTH_ACT, run)
    assert result["accepted"] == []
    assert result["undecided"] == []
    assert result["rejected"] == {"activation-1": "invalid"}


def test_non_dict_activation_is_rejected_invalid_not_a_crash():
    run = {"activations": [["x"], "junk", None]}
    result = reason_loomground(FANOUT_BOTH_ACT, run)
    assert result["accepted"] == []
    assert result["undecided"] == []
    assert result["rejected"] == {
        "activation-1": "invalid", "activation-2": "invalid", "activation-3": "invalid",
    }


def test_malformed_activations_do_not_abort_the_batch():
    run = {"activations": [
        {"actor": "a", "source": "src", "token": ["x"]},
        {"actor": "a", "source": "src", "token": {
            "id": "t1", "kind": "act", "risk": "low",
            "party": "deployer", "provenance": []}},
    ]}
    result = reason_loomground(FANOUT_BOTH_ACT, run)
    assert result["rejected"] == {"activation-1": "invalid"}
    assert result["accepted"] == ["t1"]
    assert result["undecided"] == []


OBLIGATION_UNATTACHED = """\
actor a
gate src risk low grant a
gate b risk low grant a
gate c risk low grant a
obligation log on src
cord a -> src
cord src -> b
cord src -> c
cord b -> master
cord c -> master
"""


def test_non_dict_activation_with_risk_table_is_rejected_not_a_crash():
    run = {"activations": [
        ["x"],
        {"actor": "a", "source": "src", "token": {
            "id": "t1", "kind": "act", "risk": "low",
            "party": "deployer", "provenance": []}},
    ]}
    result = reason_loomground(FANOUT_BOTH_ACT, run, risk_table=GovernedRiskTable())
    assert result["rejected"] == {"activation-1": "invalid"}
    assert result["accepted"] == ["t1"]
    assert result["undecided"] == []


def test_non_dict_token_with_risk_table_is_rejected_not_a_crash():
    run = {"activations": [
        {"actor": "a", "source": "src", "token": "junk"},
        {"actor": "a", "source": "src", "token": {
            "id": "t1", "kind": "act", "risk": "low",
            "party": "deployer", "provenance": []}},
    ]}
    result = reason_loomground(FANOUT_BOTH_ACT, run, risk_table=GovernedRiskTable())
    assert result["rejected"] == {"activation-1": "invalid"}
    assert result["accepted"] == ["t1"]
    assert result["undecided"] == []


def test_unattached_obligation_withhold_reports_auto_as_the_reason():
    result = reason_loomground(OBLIGATION_UNATTACHED, fanout_transport())
    assert result["accepted"] == []
    assert result["undecided"] == []
    assert result["rejected"] == {"t1": "auto"}
    assert result["trace"]["evaluation"]["b"] == {"verdict": "auto", "master": "withhold"}
    assert result["trace"]["evaluation"]["c"] == {"verdict": "auto", "master": "withhold"}
