import pytest

from loomground_solver.addons import AdvisorPolicy, advise, skill_manifest


def test_world_model_is_recommended_by_explicit_mathematical_threshold():
    result = advise({
        "policy": {"world_model": {"mode": "recommend", "threshold": 2}},
        "problem": {
            "as_of": "2026-07-19T00:00:00Z",
            "sources": ["s1", "s2"],
            "claims_may_conflict": True,
            "available_inputs": ["context_provider", "contradiction-policy"],
        },
    })
    world = result["recommendations"][0]
    assert world["score"] == 3 and world["threshold"] == 2
    assert world["eligible"] and world["recommended"]
    assert result["activation_performed"] is False


def test_off_policy_overrides_problem_shape():
    world = advise({"problem": {"as_of": "now", "claims_may_conflict": True}})[
        "recommendations"][0]
    assert not world["eligible"] and "disabled-by-policy" in world["reasons"]


def test_metacognition_scheduled_requires_verified_single_scope_runs():
    payload = {
        "policy": {"metacognition": {"mode": "scheduled", "minimum_runs": 3}},
        "runs": [
            {"run_id": f"r{i}", "verified": True, "scope_id": "a",
             "proposal_reviewer": "human:1"} for i in range(3)
        ],
    }
    meta = advise(payload)["recommendations"][1]
    assert meta["eligible"] and meta["recommended"] and meta["score"] == 3


def test_manual_metacognition_is_eligible_but_never_auto_recommended():
    policy = {"metacognition": {"mode": "manual", "minimum_runs": 1}}
    meta = advise({"policy": policy, "runs": [
        {"verified": True, "scope_id": "a", "proposal_reviewer": "h"}
    ]})["recommendations"][1]
    assert meta["eligible"] and not meta["recommended"]
    assert "manual-trigger-required" in meta["reasons"]


def test_bad_modes_fail_closed_and_skill_has_no_side_effects():
    with pytest.raises(ValueError):
        AdvisorPolicy(world_model="automatic")
    assert skill_manifest()["side_effects"] == []
