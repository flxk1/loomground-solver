"""Compatibility surface retained for RVND after extracting Solver."""

import importlib

import pytest


MODULE_API = {
    "loomground_solver.dimensions": {
        "Dimension", "DEFAULT_DIMENSION", "COMPOSITION_TABLE", "compose",
        "compose_weights", "classify_query_dimension", "classify_predicate",
    },
    "loomground_solver.reasoning": {
        "Edge", "Inference", "compose_paths", "extract_edges",
    },
    "loomground_solver.predicate": {
        "Predicate", "PredicateError", "PREDICATE_CONFIDENCE_FLOOR",
        "parse_condition", "attach_predicates",
    },
    "loomground_solver.temporal": {
        "Date", "Duration", "RelativeDeadline", "RenewalRule", "Term", "Money",
        "TemporalError", "validate_iso_instant", "weekend_shift",
    },
    "loomground_solver.norm_contract": {
        "Level", "Finding", "ContractReport", "check_pair", "enforce", "gate",
    },
    "loomground_solver.phases": {
        "PHASE_ORDER", "brief", "curriculum", "all_briefs",
    },
    "loomground_solver.topology": {
        "SolverNode", "Dep", "validate_topology", "topo_order", "build_topology",
    },
    "loomground_solver.contract": {
        "PROFILES", "DEFAULT_PROFILE", "check_case", "check_export", "gate",
    },
}


@pytest.mark.parametrize("module,names", MODULE_API.items())
def test_rvnd_compatibility_surface(module, names):
    imported = importlib.import_module(module)
    missing = sorted(name for name in names if not hasattr(imported, name))
    assert not missing, f"{module} is missing compatibility names: {missing}"


def test_folder_policy_adapter_does_not_leak_into_solver():
    contract = importlib.import_module("loomground_solver.contract")
    assert not hasattr(contract, "check_folder_case")
