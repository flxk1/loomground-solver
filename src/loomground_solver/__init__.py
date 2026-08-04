# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground_solver — the universal reasoning substrate.

A standalone, importable package with no governance and no domain/corpus
coupling. Governance and corpus arrive through the injected ports in
:mod:`loomground_solver.ports`. The package is imported unchanged by any host.
"""

from __future__ import annotations

# version — the single runtime version source (kept in lockstep with pyproject)
from ._version import __version__

# dimensions — the 5D edge model + algebra
from .dimensions import Dimension, compose, compose_weights

# reasoning — composing inferences over the dimensioned graph
from .reasoning import Edge, Inference, InferenceList, extract_edges, compose_paths

# graph — neighbourhood + graph-prep primitives around composition
from .graph import neighborhood, to_undirected

# relation — the typed-relation composition algebra (mechanism; table injected)
from .relation import ESCALATE, RelationAlgebra

# norm_contract — the shared verdict vocabulary
from .norm_contract import Finding, Level, ContractReport

# contract — the reasoning contract (governance-free)
from .contract import (
    check_case, gate, ReasoningViolation,
    PROFILES, DEFAULT_PROFILE, INFORMATION_FORMS,
)

# topology — validated solver DAGs
from .topology import (
    SolverNode, Dep, validate_topology, topo_order, build_topology,
)

# case — the pure case-record subset
from .case import Ground, Fact, CaseRecord, project_pairs

# ports — the injected seams
from .ports import (
    NormSource, EvidenceProvider, CandidateProvider, StructuralCompiler,
    ReasoningService, ModelFn, Governance, NullGovernance, Signer,
)

# interop application layer — provider-neutral request verification
from .evidence import InlineEvidenceProvider
from .structural import NeutralStructuralCompiler, CompilerRegistry
from .configuration import SolverConfiguration, ConfigurationResolver, NormContractProfile
from .handler import UniversalHandler, verify_request
from .service import SolverService, default_service
from .validation import ValidationError, validate_request, validate_result

# rulepacks — the pluggable typed-inference / conflict packs (rung 4)
from .rulepacks import RulePack, Ordering, GENERIC_PACK, LEX_CONFLICT_PACK, PACKS

# scenario — reasoning inside a possible world (rung 4)
from .scenario import (
    Scenario, Norm, ScenarioResult, ActResolution, derive, compare, to_case,
)

# decision — the deterministic bounded choice space (rung 4)
from .decision import DecisionSpace, decision_space, grounded_labels

# fingerprint — pluggable-filter problem-solution fingerprint (rung 4)
from .fingerprint import (
    fingerprint, distance, signature, register_filter, FILTERS, FP_VERSION,
)

# subsumption — the Tatbestand→facts step + end-to-end rule reasoning (rung 3)
from .subsumption import (
    Rule, Subsumption, subsume, applicable_rules, holds, neg, to_norms,
    apply as forward_chain, solve as solve_rules,
)

# methods — the open family of reasoning methods (rule-nD)
from .methods import METHODS, register_method, method, methods_by_kind

# replay — signed, replayable provenance (rung 4)
from .replay import (HashSigner, contextual_trace, provenance, sign,
                     sign_contextual, verify, verify_contextual, verify_trace)

# interpret — the LLM-interpretation bridge (rung 3)
from .interpret import interpret, audit, audit_text

# datapump — the verifier data-pump: verified runs -> training data (rung 4)
from .datapump import harvest, to_jsonl

# federation — reasoning in fingerprint space (narrow a solution by inference)
from .federation import structural_transform, derive_solution

# api — the product surface
from .api import entail, plan, check, narrow

# Loomground language route
from .loomground import (
    ApplyError, ParseError, apply as apply_loomground, evaluate as evaluate_loomground,
    parse as parse_loomground, project as observe_loomground, reason as reason_loomground,
)

# universal system adapters — product-native 5D+nD projection
from .adapters import (
    AdapterCapabilities, AdapterRegistry, CoordinateAssignment, LoomgroundAdapter,
    NDSystem, SolverProjection, SystemAdapter, SystemIdentity, VersumNormSource,
    adapt_loomground, install_reference_filters,
)

__all__ = [
    # version
    "__version__",
    # dimensions
    "Dimension", "compose", "compose_weights",
    # reasoning
    "Edge", "Inference", "InferenceList", "extract_edges", "compose_paths",
    # graph — neighbourhood + graph-prep primitives
    "neighborhood", "to_undirected",
    # relation composition (mechanism; domain supplies the table)
    "RelationAlgebra", "ESCALATE",
    # norm_contract
    "Finding", "Level", "ContractReport",
    # contract
    "check_case", "gate", "ReasoningViolation",
    "PROFILES", "DEFAULT_PROFILE", "INFORMATION_FORMS",
    # topology
    "SolverNode", "Dep", "validate_topology", "topo_order", "build_topology",
    # case
    "Ground", "Fact", "CaseRecord", "project_pairs",
    # ports
    "NormSource", "EvidenceProvider", "CandidateProvider", "StructuralCompiler",
    "ReasoningService", "ModelFn", "Governance", "NullGovernance", "Signer",
    # interop application layer
    "InlineEvidenceProvider", "NeutralStructuralCompiler", "CompilerRegistry",
    "SolverConfiguration", "ConfigurationResolver", "NormContractProfile",
    "UniversalHandler",
    "verify_request", "SolverService", "default_service", "ValidationError",
    "validate_request", "validate_result",
    # rulepacks (rung 4)
    "RulePack", "Ordering", "GENERIC_PACK", "LEX_CONFLICT_PACK", "PACKS",
    # scenario (rung 4)
    "Scenario", "Norm", "ScenarioResult", "ActResolution",
    "derive", "compare", "to_case",
    # decision (rung 4)
    "DecisionSpace", "decision_space", "grounded_labels",
    # fingerprint (rung 4)
    "fingerprint", "distance", "signature", "register_filter", "FILTERS", "FP_VERSION",
    # subsumption + rule reasoning (rung 3)
    "Rule", "Subsumption", "subsume", "applicable_rules", "holds", "neg",
    "to_norms", "forward_chain", "solve_rules",
    # methods (rule-nD)
    "METHODS", "register_method", "method", "methods_by_kind",
    # replay (rung 4)
    "HashSigner", "provenance", "verify_trace", "sign", "verify",
    "contextual_trace", "sign_contextual", "verify_contextual",
    # interpret (rung 3)
    "interpret", "audit", "audit_text",
    # datapump (rung 4)
    "harvest", "to_jsonl",
    # federation — reasoning in fingerprint space
    "structural_transform", "derive_solution",
    # api
    "entail", "plan", "check", "narrow",
    # Loomground language route
    "ApplyError", "ParseError", "apply_loomground", "evaluate_loomground",
    "parse_loomground", "observe_loomground", "reason_loomground",
    # universal system adapters
    "AdapterCapabilities", "AdapterRegistry", "CoordinateAssignment",
    "LoomgroundAdapter", "NDSystem", "SolverProjection", "SystemAdapter",
    "SystemIdentity", "VersumNormSource", "adapt_loomground",
    "install_reference_filters",
]
