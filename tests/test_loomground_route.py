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


RISK_TABLE_FLOOR_RAISE = """\
actor bot
gate decide risk high grant bot
cord bot -> decide
cord decide -> master
"""


def test_risk_table_log_token_is_the_declared_token_not_the_governed_one():
    """§7.4: when a risk_table governs the token (PROM-001) AND the gate's own
    floor then raises risk further, the log's `token` field MUST be the
    DECLARED token the actor presented — never the governed one evaluate()
    actually ran against. The actor declares `risk low`; the risk table
    governs that up to `medium` (host-observed kind matches the declared one,
    so PROM-001's kind-mismatch floor never fires — only the raise-only risk
    ratchet is exercised); `decide`'s own floor (`high`) then raises it
    again. The entry's `token.risk` must read the actor's original `low`
    claim, never the table-governed `medium` nor the gate-floored `high`.
    Also: a copy, not a live reference — mutating the original token after
    the call must not retroactively change the already-built log entry."""
    declared_token = {"id": "t1", "kind": "deploy_action", "risk": "low",
                       "party": "deployer", "provenance": []}
    run = {"activations": [{
        "actor": "bot", "source": "decide", "token": declared_token,
        "observed": {"kind": "deploy_action"},
    }]}
    risk_table = GovernedRiskTable(entries={("deploy_action", "", "", ""): "medium"})

    result = reason_loomground(RISK_TABLE_FLOOR_RAISE, run, risk_table=risk_table)

    entry = result["trace"]["log"][0]
    assert entry["gate"] == "decide"
    assert entry["token"] == declared_token
    assert entry["token"]["risk"] == "low"                 # declared, never "medium" (table) or "high" (floor)
    assert entry["observed"] == {"kind": "deploy_action", "risk": "high"}
    assert entry["token"] is not declared_token            # a snapshot, not a live reference

    declared_token["risk"] = "critical"
    assert result["trace"]["log"][0]["token"]["risk"] == "low", (
        "mutating the caller's token after the call must not change the log")


def test_log_token_survives_nested_provenance_mutation():
    """A shallow `dict(...)` copy would still share a nested list
    (`provenance`) with the caller's token — mutating that list in place
    after the call must not retroactively change an already-built log
    entry. Exercises the plain (no risk_table) path, where `decide`'s own
    floor (high) raises the declared `low` risk."""
    declared_token = {"id": "t1", "kind": "act", "risk": "low",
                       "party": "deployer", "provenance": ["src1"]}
    run = {"activations": [{
        "actor": "bot", "source": "decide", "token": declared_token,
    }]}

    result = reason_loomground(RISK_TABLE_FLOOR_RAISE, run)

    entry = result["trace"]["log"][0]
    assert entry["token"]["provenance"] == ["src1"]

    declared_token["provenance"].append("mutated-after-the-fact")
    assert result["trace"]["log"][0]["token"]["provenance"] == ["src1"], (
        "mutating a nested list on the caller's token after the call "
        "must not change the log (deep, not shallow, copy)")


@pytest.mark.parametrize("forged", [
    "not-a-dict", 123, None, ["x"], {"id": "forged", "kind": "forged",
                                      "risk": "critical", "party": "x", "provenance": []},
])
def test_declared_token_activation_key_is_ignored_and_cannot_forge_or_crash(forged):
    """An activation is never trusted to carry its own `_declared_token` —
    that key is purely internal plumbing between reason()'s risk_table
    governance step and `_evaluate_with_log`'s log-building step, passed as
    a private positional list, never read off the activation dict. A caller
    putting ANY value under that key on its own activation — including a
    non-dict that would crash a naive `dict(...)`/attribute read, or a
    well-formed but false token aimed at forging the §7.4 record — must be
    silently ignored: the log must show the activation's REAL own token,
    and the call must not crash."""
    declared_token = {"id": "t1", "kind": "act", "risk": "low",
                       "party": "deployer", "provenance": []}
    run = {"activations": [{
        "actor": "bot", "source": "decide", "token": declared_token,
        "_declared_token": forged,
    }]}

    result = reason_loomground(RISK_TABLE_FLOOR_RAISE, run)

    entry = result["trace"]["log"][0]
    assert entry["token"] == declared_token
    assert entry["token"]["kind"] == "act"
    assert entry["token"]["risk"] == "low"


def test_unattached_obligation_withhold_reports_auto_as_the_reason():
    result = reason_loomground(OBLIGATION_UNATTACHED, fanout_transport())
    assert result["accepted"] == []
    assert result["undecided"] == []
    assert result["rejected"] == {"t1": "auto"}
    assert result["trace"]["evaluation"]["b"] == {"verdict": "auto", "master": "withhold"}
    assert result["trace"]["evaluation"]["c"] == {"verdict": "auto", "master": "withhold"}


# ── fuzz: every activation-derived value reason()/PROM-001 dereference ──────────
# .get, indexing, iteration, RISK_RANK-style membership, hashing — must fail
# closed to "invalid" for a malformed shape, never raise, never abort the batch,
# and must never let a token slip past governance ungoverned (risk_table path).
#
# A generic non-dict/non-list/None/int/str sweep is used everywhere a value
# must be a MAPPING (the activation, the token) or a MEMBER of a fixed table
# (risk/reversibility/uncertainty/provenance, where a wrong-typed value and a
# wrong *string* are equally invalid). Free-text string fields (source/actor/
# id/kind/party/observed.*) legitimately accept ANY string — "junk" there is
# a normal, if meaningless, value (an unknown gate id just "refused"s, it
# does not crash) — so those sweeps drop the bare string and, where the
# field is itself OPTIONAL (actor, token.tags), drop ``None`` too.
# ``observed.*`` only matters on the risk_table path (§ absent risk_table,
# `observed` is never read) — those cases are risk_table-only.
_GENERIC = ("junk", 123, None, [1, 2], {}, True, {"nested": "x"})
_NON_STRING = tuple(v for v in _GENERIC if v != "junk")
_NON_STRING_NONE_OK = tuple(v for v in _NON_STRING if v is not None)
BOTH = ({}, {"risk_table": GovernedRiskTable()})
RISK_TABLE_ONLY = ({"risk_table": GovernedRiskTable()},)


def _malformed_token():
    return {"id": "bad", "kind": "act", "risk": "low",
            "party": "deployer", "provenance": []}


def _valid_sibling():
    return {"actor": "a", "source": "src", "token": {
        "id": "sibling", "kind": "act", "risk": "low",
        "party": "deployer", "provenance": []}}


def _fanout_fuzz_cases():
    cases = []

    def add(label, value, act, kwargs_variants):
        for kwargs in kwargs_variants:
            cases.append((label, value, act, kwargs))

    for v in _GENERIC:
        add("activation", v, v, BOTH)
        add("token", v, {"actor": "a", "source": "src", "token": v}, BOTH)
    for v in _NON_STRING:
        add("source", v, {"actor": "a", "source": v, "token": _malformed_token()}, BOTH)
        for field in ("id", "kind", "party"):
            add(f"token.{field}", v, {"actor": "a", "source": "src",
                                       "token": {**_malformed_token(), field: v}}, BOTH)
    for v in _NON_STRING_NONE_OK:
        add("actor", v, {"actor": v, "source": "src", "token": _malformed_token()}, BOTH)
        for field in ("kind", "target", "context", "grade"):
            add(f"observed.{field}", v, {"actor": "a", "source": "src",
                                          "token": _malformed_token(),
                                          "observed": {field: v}}, RISK_TABLE_ONLY)
    for v in _GENERIC:  # membership/list fields: a wrong string is exactly as invalid as a wrong type
        for field in ("risk", "provenance", "reversibility", "uncertainty"):
            add(f"token.{field}", v, {"actor": "a", "source": "src",
                                       "token": {**_malformed_token(), field: v}}, BOTH)
    for v in _NON_STRING_NONE_OK:  # tags: absent/None is legal, everything else must be list[str]
        add("token.tags", v, {"actor": "a", "source": "src",
                               "token": {**_malformed_token(), "tags": v}}, BOTH)
    return cases


@pytest.mark.parametrize("label, value, malformed_activation, risk_table_kwargs",
                          _fanout_fuzz_cases(), ids=lambda x: repr(x)[:40])
def test_malformed_activation_fields_never_crash_and_reject_invalid(
        label, value, malformed_activation, risk_table_kwargs):
    run = {"activations": [malformed_activation, _valid_sibling()]}
    result = reason_loomground(FANOUT_BOTH_ACT, run, **risk_table_kwargs)
    assert result["accepted"] == ["sibling"]
    assert result["undecided"] == []
    assert len(result["rejected"]) == 1
    assert list(result["rejected"].values()) == ["invalid"]
