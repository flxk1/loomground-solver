from dataclasses import replace

import pytest

from loomground_solver.addons.metacognition import (
    JsonlProposalStore, ProposalStatus, observe, recurring_gap_proposals,
)

VERIFIED = lambda _record: True


def test_observation_requires_immutable_replay_identity():
    with pytest.raises(ValueError, match="verification failed"):
        observe({"run_id": "r1", "signature": "forged"}, verifier=lambda _r: False)
    with pytest.raises(ValueError):
        observe({"run_id": "r1", "gaps": []}, verifier=VERIFIED)
    item = observe({"run_id": "r1", "signature": "sha256:x", "decision": "open",
                    "gaps": ["Missing governing source"]}, verifier=VERIFIED,
                   scope_id="tenant-a")
    assert item.replay_digest == "sha256:x" and item.scope_id == "tenant-a"


def test_recurring_gaps_produce_stable_draft_not_mutation():
    observations = [
        observe({"run_id": f"r{i}", "signature": f"sha256:{i}",
                 "decision": "open", "gaps": ["Missing governing source"]},
                verifier=VERIFIED)
        for i in range(3)
    ]
    first = recurring_gap_proposals(observations)
    second = recurring_gap_proposals(reversed(observations))
    assert first == second and len(first) == 1
    assert first[0].status is ProposalStatus.DRAFT
    assert first[0].authorization_ref is None


def test_store_is_scope_isolated_and_cannot_promote(tmp_path):
    proposal = recurring_gap_proposals([
        observe({"run_id": f"r{i}", "signature": f"s{i}", "gaps": ["same gap"]},
                verifier=VERIFIED,
                scope_id="a") for i in range(3)
    ])[0]
    store = JsonlProposalStore(tmp_path)
    store.append(proposal)
    assert store.load("a") == (proposal,)
    assert store.load("b") == ()
    with pytest.raises(ValueError):
        store.append(replace(proposal, status=ProposalStatus.PROMOTED,
                             authorization_ref="approval:1"))
