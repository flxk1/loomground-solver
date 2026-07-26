from loomground_solver.addons.metacognition import (
    ImprovementKind,
    ImprovementProposal,
    ProposalStatus,
)
from loomground_solver.addons.world_model import Belief, ContextSnapshot, Freshness


def test_world_model_snapshot_is_immutable_and_explicit():
    belief = Belief(
        belief_id="belief:1",
        proposition={"subject": "x", "predicate": "is", "object": "y"},
        evidence_refs=("evidence:1",),
        observed_at="2026-07-19T00:00:00Z",
        freshness=Freshness.CURRENT,
    )
    snapshot = ContextSnapshot(
        snapshot_id="snapshot:1",
        created_at="2026-07-19T00:00:00Z",
        beliefs=(belief,),
    )
    assert snapshot.beliefs == (belief,)


def test_metacognition_starts_as_a_proposal_not_a_mutation():
    proposal = ImprovementProposal(
        proposal_id="proposal:1",
        kind=ImprovementKind.TEST,
        motivating_runs=("run:1",),
        proposed_change={"add_case": "recurring-gap"},
    )
    assert proposal.status is ProposalStatus.DRAFT
    assert proposal.authorization_ref is None
