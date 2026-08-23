# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Loomground 0.9 -> 0.11 vocabulary: mandate/transfer/consign, the
reversibility/uncertainty guard fields, the ISO/IEC 22989 autonomy ladder
(0-6), and role canonicalization. The governance conformance runner
(scripts/run_loomground_conformance.py) is the authority on these vectors;
this file adds solver-level unit coverage a conformance run does not, and
pins the concrete values the deliverable cites."""
import pytest

from loomground_solver.loomground import (
    GRADES, GUARD_FIELDS, GUARD_OPS, REVERSIBILITY_RANK, SUPPORTED_LANGUAGE_VERSIONS,
    UNCERTAINTY_RANK, ApplyError, apply, canonical_roles, canonicalize_role,
    evaluate, grade_rank, project, to_netlist,
)


# ── version + guard-domain surface (acceptance §4) ─────────────────────────

def test_supported_language_versions_includes_0_11():
    assert "0.11" in SUPPORTED_LANGUAGE_VERSIONS
    assert "0.9" in SUPPORTED_LANGUAGE_VERSIONS
    assert "0.10" in SUPPORTED_LANGUAGE_VERSIONS


def test_guard_fields_include_reversibility_and_uncertainty():
    assert GUARD_FIELDS == {"kind", "risk", "reversibility", "uncertainty", "party", "tags"}
    assert GUARD_OPS["reversibility"] == {">=", "="}
    assert GUARD_OPS["uncertainty"] == {">=", "="}


def test_autonomy_ladder_is_the_iso_22989_seven_level_axis():
    assert GRADES == ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]
    assert grade_rank("L6") == 6
    assert grade_rank(6) == 6          # an adapter integer rank at the new ceiling
    assert grade_rank(7) == -1         # one past the ladder is unrecognised (fail-safe)


# ── role canonicalization (v0.10.0) — consumed, never re-declared ──────────

def test_role_canonicalization_is_consumed_from_governance():
    resolved = canonicalize_role("the data protection officer")
    assert resolved == {"role": "data protection officer", "kind": "human"}
    assert canonicalize_role("nothing matches this span") is None
    assert any(entry["role"] == "controller" for entry in canonical_roles())


# ── mandate (v0.9.0) ─────────────────────────────────────────────────────

MANDATE_CHAIN = """\
actor board mandate {deploy,procure,rollback}
actor lead on-behalf-of board mandate {deploy,rollback}
actor agent on-behalf-of lead mandate deploy
gate g risk low grant board[deploy:low] lead[deploy:low] agent[deploy:low]
cord g -> master
"""


def test_mandate_projects_as_ascending_lexicographic_set():
    patch = apply(MANDATE_CHAIN)
    obs = project(patch)
    by_id = {n["id"]: n for n in obs["nodes"]}
    assert by_id["board"]["mandate"] == ["deploy", "procure", "rollback"]
    assert by_id["lead"]["mandate"] == ["deploy", "rollback"]
    assert by_id["agent"]["mandate"] == ["deploy"]


def test_mandate_attenuation_composes_pairwise_along_the_chain():
    # well-formed: each link narrows (board -> lead -> agent), never widens.
    apply(MANDATE_CHAIN)  # does not raise


def test_mandate_widen_is_ill_formed_at_apply():
    source = (
        "actor boss mandate deploy\n"
        "actor sub on-behalf-of boss mandate {deploy,procure}\n"
        "gate g risk low grant boss[deploy:low] sub[deploy:low]\n"
        "cord g -> master\n"
    )
    with pytest.raises(ApplyError, match="widens"):
        apply(source)


def test_mandate_from_nothing_is_ill_formed_at_apply():
    source = (
        "actor boss\n"
        "actor sub on-behalf-of boss mandate deploy\n"
        "gate g risk low grant boss[deploy:low] sub[deploy:low]\n"
        "cord g -> master\n"
    )
    with pytest.raises(ApplyError):
        apply(source)


def test_mandate_duplicate_is_ill_formed_at_apply():
    source = (
        "actor boss mandate {deploy,rollback}\n"
        "actor sub on-behalf-of boss mandate deploy mandate rollback\n"
        "gate g risk low grant boss[deploy:low] sub[deploy:low]\n"
        "cord g -> master\n"
    )
    with pytest.raises(ApplyError, match="more than one mandate"):
        apply(source)


def test_mandate_round_trips_through_to_netlist():
    patch = apply(MANDATE_CHAIN)
    reparsed = apply(to_netlist(patch))
    assert project(reparsed) == project(patch)


# ── consign + transfer (v0.9.0) ─────────────────────────────────────────

HANDOFF = """\
actor  counsel  mandate {review,draft,advise}
human  partner  role supervising-partner
gate   assemble risk low                   grant counsel[work_product:low,high]
gate   release  risk high consign vendorb  grant counsel[work_product:low,high]
reserve work_product by supervising-partner when reversibility >= irreversible
transfer work_product to vendorb within review
cord counsel  -> assemble
cord counsel  -> release
cord assemble -> release
cord release  -> master
"""


def test_consign_and_transfer_project_as_the_spec_shape():
    patch = apply(HANDOFF)
    obs = project(patch)
    by_id = {n["id"]: n for n in obs["nodes"]}
    assert by_id["release"]["consignee"] == "vendorb"
    assert obs["transfers"] == [{"kind": "work_product", "to": "vendorb", "within": ["review"]}]


def test_consign_on_interior_gate_is_ill_formed_at_apply():
    source = (
        "actor counsel mandate review\n"
        "gate  draft   risk low consign vendorb grant counsel[work_product:low]\n"
        "gate  release risk low                 grant counsel[work_product:low]\n"
        "cord draft   -> release\n"
        "cord release -> master\n"
    )
    with pytest.raises(ApplyError, match="non-terminal"):
        apply(source)


def test_transfer_widen_beyond_mandate_is_ill_formed_at_apply():
    source = (
        "actor counsel mandate review\n"
        "gate  release risk low consign vendorb grant counsel[work_product:low]\n"
        "transfer work_product to vendorb within {review,advise}\n"
        "cord release -> master\n"
    )
    with pytest.raises(ApplyError, match="exceed the mandate"):
        apply(source)


def test_transfer_unmandated_actor_licenses_nothing_onward():
    source = (
        "actor counsel\n"
        "gate  release risk low consign vendorb grant counsel[work_product:low]\n"
        "transfer work_product to vendorb within review\n"
        "cord release -> master\n"
    )
    with pytest.raises(ApplyError, match="exceed the mandate"):
        apply(source)


def test_transfer_to_a_dangling_consignee_is_ill_formed_at_apply():
    source = (
        "actor counsel mandate review\n"
        "gate  release risk low grant counsel[work_product:low]\n"
        "transfer work_product to vendorb within review\n"
        "cord release -> master\n"
    )
    with pytest.raises(ApplyError, match="no gate declares"):
        apply(source)


def test_handoff_reservation_fires_on_irreversible_and_withholds():
    patch = apply(HANDOFF)
    transport = {"activations": [{
        "actor": "counsel", "source": "assemble",
        "token": {"id": "t1", "kind": "work_product", "risk": "high",
                  "party": "firm", "provenance": [], "reversibility": "irreversible"},
    }]}
    result = evaluate(patch, transport)
    assert result["assemble"]["verdict"] == "reserved"
    assert result["release"] == {"verdict": "reserved", "master": "withhold"}


def test_handoff_round_trips_through_to_netlist():
    patch = apply(HANDOFF)
    reparsed = apply(to_netlist(patch))
    assert project(reparsed) == project(patch)


# ── reversibility / uncertainty guards (v0.9.0) ─────────────────────────

def test_reversibility_guard_absent_property_never_matches():
    source = (
        "actor bot7\n"
        "human alice role safety\n"
        "gate  hard risk low grant bot7\n"
        "reserve deploy by safety when reversibility >= irreversible\n"
        "cord bot7 -> hard\n"
        "cord hard -> master\n"
    )
    patch = apply(source)
    bare = {"activations": [{"actor": "bot7", "source": "hard", "token": {
        "id": "t1", "kind": "deploy", "risk": "low", "party": "deployer", "provenance": []}}]}
    assert evaluate(patch, bare)["hard"]["verdict"] == "auto"


def test_reject_bad_reversibility_value_at_apply():
    source = (
        "actor bot7\n"
        "gate  act risk low grant bot7\n"
        "reserve deploy by safety when reversibility >= permanent\n"
        "cord bot7 -> act\n"
        "cord act  -> master\n"
    )
    with pytest.raises(ApplyError):
        apply(source)


def test_reject_reversibility_with_contains_operator_at_apply():
    source = (
        "actor bot7\n"
        "gate  act risk low grant bot7\n"
        "reserve deploy by safety when reversibility contains irreversible\n"
        "cord bot7 -> act\n"
        "cord act  -> master\n"
    )
    with pytest.raises(ApplyError):
        apply(source)


def test_uncertainty_guard_is_orthogonal_to_risk():
    source = (
        "actor  bot7\n"
        "human  alice role review\n"
        "gate   open  risk low grant bot7\n"
        "reserve claim by review when uncertainty >= contested\n"
        "cord bot7 -> open\n"
        "cord open -> master\n"
    )
    patch = apply(source)
    contested = {"activations": [{"actor": "bot7", "source": "open", "token": {
        "id": "t1", "kind": "claim", "risk": "low", "party": "deployer",
        "provenance": [], "uncertainty": "contested"}}]}
    assert evaluate(patch, contested)["open"]["verdict"] == "reserved"


def test_reversibility_and_uncertainty_domains_are_governance_sourced():
    assert list(REVERSIBILITY_RANK) == ["reversible", "compensable", "irreversible"]
    assert list(UNCERTAINTY_RANK) == ["settled", "contested", "unknown"]
