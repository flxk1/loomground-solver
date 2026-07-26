import pytest

from loomground_solver.addons.metacognition import (
    ArtifactVersion, EvaluationCase, EvaluationPartition, ImprovementKind,
    ImprovementProposal, JsonlVersionRegistry, ProposalStatus, SignedRunRecord,
    authorize, evaluate_proposal, observe_record, promote, rollback,
)


def _proposal():
    return ImprovementProposal("p:1", ImprovementKind.TEST, ("r:1",),
                               {"add_case": "gap"})


def _cases(fail=""):
    return tuple(
        EvaluationCase(part.value, part, {"case": part.value}, {"ok": True})
        for part in EvaluationPartition
    )


def test_typed_observer_requires_verifier_port():
    record = SignedRunRecord("r:1", "sha256:x", "undecided", ("gap",), "scope")

    class Verifier:
        def verify(self, value):
            return value is record

    observed = observe_record(record, verifier=Verifier())
    assert observed.run_id == "r:1" and observed.scope_id == "scope"
    with pytest.raises(ValueError, match="verification failed"):
        observe_record(record, verifier=lambda _record: False)


def test_evaluation_requires_training_regression_and_holdout_to_pass():
    proposal, report = evaluate_proposal(_proposal(), _cases(),
                                         runner=lambda _proposal, _case: True)
    assert report.eligible and report.passed == 4
    assert proposal.status is ProposalStatus.EVALUATED
    assert set(report.partitions) == {p.value for p in EvaluationPartition}

    incomplete, report = evaluate_proposal(_proposal(), _cases()[:2],
                                            runner=lambda _proposal, _case: True)
    assert not report.eligible and not incomplete.evaluation["eligible"]


def test_authorize_promote_and_rollback_are_evidence_bearing(tmp_path):
    evaluated, _ = evaluate_proposal(_proposal(), _cases(),
                                     runner=lambda _proposal, _case: True)
    authorized = authorize(evaluated, "approval:human:1")
    promoted, version = promote(authorized, {"test": "new"}, version_id="v2",
                                predecessor="v1")
    assert promoted.status is ProposalStatus.PROMOTED
    assert version.authorization_ref == "approval:human:1"
    previous = ArtifactVersion("v1", "p:old", "sha256:" + "0" * 64,
                               "approval:old")
    record = rollback(version, previous, authorization_ref="approval:rollback",
                      evidence_refs=("case:regression",))
    registry = JsonlVersionRegistry(tmp_path)
    registry.append("scope-a", version)
    registry.append("scope-a", record)
    assert registry.load("scope-a") == (version, record)
    assert registry.load("scope-b") == ()


def test_lifecycle_fails_closed_without_evaluation_authorization_or_evidence():
    with pytest.raises(ValueError):
        authorize(_proposal(), "approval:x")
    evaluated, _ = evaluate_proposal(_proposal(), _cases(),
                                     runner=lambda _proposal, case:
                                     case.partition is not EvaluationPartition.HOLDOUT)
    with pytest.raises(ValueError):
        authorize(evaluated, "approval:x")
    with pytest.raises(ValueError):
        rollback(ArtifactVersion("v2", "p", "d", "a"),
                 ArtifactVersion("v1", "p", "d", "a"),
                 authorization_ref="", evidence_refs=())
