from loomground_solver import (
    Norm, Scenario, derive, sign_contextual, verify_contextual,
)
from loomground_solver.addons.world_model import Belief, make_snapshot


def test_replay_signature_binds_exact_context_snapshot():
    scenario = Scenario("s", norms=[Norm("act", "permitted")])
    first = make_snapshot([Belief("b", {"x": 1}, ("e",), "2026-01-01T00:00:00Z")],
                          created_at="2026-07-19T00:00:00Z")
    second = make_snapshot([Belief("b", {"x": 2}, ("e",), "2026-01-01T00:00:00Z")],
                           created_at="2026-07-19T00:00:00Z")
    signature = sign_contextual(derive(scenario), first)
    assert verify_contextual(scenario, first, signature)
    assert not verify_contextual(scenario, second, signature)
