# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""PROM-001 — host-observed kind, gate-computed risk (SPEC §4, §7.4; v0.11.0).

Five points, each pinned by a test below:

1. `kind` is HOST-OBSERVED, never actor-declared.
2. `risk` is GATE-COMPUTED from a governed policy table, with a self-declared
   hint admitted ONLY as a monotonic raise-only ratchet.
3. An unmapped pattern resolves to the STRICTEST tier.
4. The fail-closed floor: unclassifiable OR declared != observed -> strictest.
5. The dual log records BOTH the declared token and the host-observed facts.
"""
from loomground_solver.prom001 import (
    STRICTEST_RISK, UNCLASSIFIABLE_KIND, GovernedRiskTable, HostObservation,
    govern_token,
)
from loomground_solver.loomground import RISK_RANK, reason


TABLE = GovernedRiskTable(
    entries={
        ("deploy_model", "prod", "eu", "L3"): "medium",
        ("deploy_model", "prod", "eu", ""): "high",
        ("read_metadata", "", "", ""): "low",
    },
    version="risk-table-v1",
)


# ── 1. kind is host-observed, never actor-declared ─────────────────────────

def test_kind_is_host_observed_not_actor_declared():
    # the actor claims a mild "read_metadata"; the host actually observed a
    # write. The governed token MUST carry the host's fact, never the claim.
    declared = {"id": "t1", "kind": "read_metadata", "party": "deployer", "provenance": []}
    observed = HostObservation(kind="deploy_model", target="prod", context="eu", grade="L3")
    out = govern_token(declared, observed, TABLE)
    assert out.kind == "deploy_model"
    assert out.token["kind"] == "deploy_model"


def test_declared_kind_never_lands_on_the_token_even_when_it_agrees():
    # even a TRUTHFUL claim is not what sets `kind` — the host observation is
    # the sole source, the actor's field is never consulted to arrive at it.
    declared = {"id": "t2", "kind": "read_metadata", "party": "deployer", "provenance": []}
    observed = HostObservation(kind="read_metadata")
    out = govern_token(declared, observed, TABLE)
    assert out.kind == observed.kind == "read_metadata"
    assert not out.floored


# ── 2. risk is gate-computed, self-declared hint is a raise-only ratchet ────

def test_risk_is_gate_computed_from_the_table():
    declared = {"id": "t3", "kind": "read_metadata", "party": "deployer", "provenance": []}
    observed = HostObservation(kind="read_metadata")
    out = govern_token(declared, observed, TABLE)
    assert out.risk == "low"                # the table's own entry, not an actor claim
    assert not out.floored


def test_self_declared_hint_raises_the_computed_tier():
    declared = {"id": "t4", "kind": "read_metadata", "risk": "critical",
                "party": "deployer", "provenance": []}
    observed = HostObservation(kind="read_metadata")
    out = govern_token(declared, observed, TABLE)
    assert out.risk == "critical"            # ratchet raised low -> critical
    assert RISK_RANK["critical"] > RISK_RANK["low"]


def test_self_declared_hint_never_lowers_the_computed_tier():
    declared = {"id": "t5", "kind": "deploy_model", "risk": "low",
                "party": "deployer", "provenance": []}
    observed = HostObservation(kind="deploy_model", target="prod", context="eu", grade="L3")
    out = govern_token(declared, observed, TABLE)
    # table computes "medium" for this exact (kind, target, context, grade);
    # the actor's "low" hint MUST NOT be honoured (raise-only, never lower).
    assert out.risk == "medium"
    assert RISK_RANK["medium"] > RISK_RANK["low"]


# ── 3. an unmapped pattern resolves to the strictest tier ──────────────────

def test_unmapped_pattern_floors_to_the_strictest_tier():
    declared = {"id": "t6", "kind": "launch_missiles", "party": "deployer", "provenance": []}
    observed = HostObservation(kind="launch_missiles")   # no table entry anywhere
    out = govern_token(declared, observed, TABLE)
    assert out.risk == STRICTEST_RISK == "critical"
    assert out.floored
    assert "unmapped" in out.floor_reason


# ── 4. fail-closed floor: unclassifiable OR declared != observed ───────────

def test_unclassifiable_operation_floors_and_never_trusts_the_actor():
    declared = {"id": "t7", "kind": "harmless_looking_claim", "party": "deployer", "provenance": []}
    observed = HostObservation(kind=None)   # host could not classify the operation at all
    out = govern_token(declared, observed, TABLE)
    assert out.kind == UNCLASSIFIABLE_KIND
    assert out.kind != declared["kind"]      # the actor's claim never buys a kind
    assert out.risk == STRICTEST_RISK
    assert out.floored


def test_declared_vs_observed_mismatch_floors_never_favours_the_token():
    declared = {"id": "t8", "kind": "read_metadata", "risk": "low",
                "party": "deployer", "provenance": []}
    observed = HostObservation(kind="deploy_model", target="prod", context="eu", grade="L3")
    out = govern_token(declared, observed, TABLE)
    assert out.kind == "deploy_model"        # host-observed governs kind regardless
    assert out.risk == STRICTEST_RISK        # the mismatch floors risk, "low" hint ignored
    assert out.floored
    assert "!=" in out.floor_reason


# ── 5. the dual log: both the declared token and the host-observed facts ───

def test_dual_log_carries_both_declared_and_observed():
    declared = {"id": "t9", "kind": "read_metadata", "risk": "low",
                "party": "deployer", "provenance": []}
    observed = HostObservation(kind="deploy_model", target="prod", context="eu", grade="L3")
    out = govern_token(declared, observed, TABLE)
    # the declared token survives verbatim in the record...
    assert out.declared == declared
    # ...alongside the host-observed facts that produced kind/risk, distinctly.
    assert out.observed["kind"] == "deploy_model"
    assert out.observed["target"] == "prod"
    assert out.observed["context"] == "eu"
    assert out.observed["grade"] == "L3"
    assert out.observed["table_version"] == "risk-table-v1"
    # a later redress can weigh the claim against the observation because
    # neither is reconciled away: they disagree on `kind` in this record.
    assert out.declared["kind"] != out.observed["kind"]


def test_reason_integration_is_additive_and_carries_the_dual_log():
    source = (
        "actor bot\n"
        "gate decide risk low grant bot\n"
        "cord bot -> decide\n"
        "cord decide -> master\n"
    )
    activation = {
        "actor": "bot", "source": "decide",
        "token": {"id": "t10", "kind": "deploy_model", "party": "deployer", "provenance": []},
        "observed": {"kind": "deploy_model", "target": "prod", "context": "eu", "grade": "L3"},
    }
    # without a risk_table: unchanged behaviour — no prom001 trace, no governance
    plain = reason(source, {"activations": [activation]})
    assert "prom001" not in plain["trace"]

    # with a risk_table: the token is governed before evaluate() sees it, and
    # the dual log lands in trace["prom001"].
    governed = reason(source, {"activations": [activation]}, risk_table=TABLE)
    assert governed["trace"]["prom001"][0]["declared"]["kind"] == "deploy_model"
    assert governed["trace"]["prom001"][0]["observed"]["kind"] == "deploy_model"
    assert governed["trace"]["prom001"][0]["kind"] == "deploy_model"
    assert governed["trace"]["prom001"][0]["risk"] == "medium"
    # the gate's floor is "low"; the governed token's risk ("medium") is what
    # the evaluation actually used — reflected in the (unaffected) verdict path.
    assert governed["trace"]["evaluation"]["decide"]["verdict"] == "auto"
