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
from .graph import Neighborhood, neighborhood, to_undirected

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

# closure — deontic permissive/prohibitive closure with polarity (O140)
from .closure import (
    AgentMode, ClosureResult, close, is_strong_permission, verdict_to_operator,
)

# consistency — universalizability / treat-like-alike (O151)
from .consistency import (
    DecidedCase, InconsistentPair, ConsistencyReport,
    check_consistency, check_nondiscrimination, terminal_state,
    decided_case_from_record,
)

# burden — burden / presumption / standard-of-proof + non-liquet (O102–O105, O107)
# (element status collapsed onto the shared cross_subsumption.Verdict: proven→SATISFIED,
# disproven→NOT_SATISFIED, non-liquet→OPEN; the burden reading lives in by_burden/against)
from .burden import (
    Standard, STANDARDS, meets,
    Element, Presumption, ElementFinding, BurdenReport, allocate,
)

# distribution — inequality + adverse-impact instrumentation, measure-only (O148, O152)
from .distribution import (
    FOUR_FIFTHS, InequalityMetrics, inequality,
    ImpactRatio, adverse_impact, rates_from_cases,
)

# justice_screen — anti-blindness value/justice screen, flag-only (O154 formal half)
# (DETERMINATE/ESCALATE terminal labels intentionally NOT re-exported: `ESCALATE`
#  would shadow the relation.ESCALATE sentinel; use justice_screen.* for those.)
from .justice_screen import (
    ScreenResult, TrippedReason, justice_screen,
    INCONSISTENCY, DISCRIMINATION, ADVERSE_IMPACT,
)

# welfare — welfare-function evaluation + Pareto/fair-division, compute-only (O149, O150)
from .welfare import (
    WELFARE_PRINCIPLES, UTILITARIAN, RAWLSIAN, PRIORITARIAN, EGALITARIAN,
    WelfareEvaluation, evaluate as welfare_evaluate,
    ParetoReport, pareto_allocations, FairDivisionReport, fair_division,
)

# proportionality — Verhältnismäßigkeit + Alexy Weight Formula, tie→ESCALATE (O94–O99)
from .proportionality import (
    proportionality, ProportionalityResult, PrincipleWeight, Alternative,
    ProngVerdict, weight_formula, necessity_holds, TRIAD, LIGHT, MODERATE, SERIOUS,
)

# principles — collision-of-principles detection + rule/principle routing (O93)
from .principles import (
    classify_collision, route_for, CollisionRouting,
    RULE, PRINCIPLE, NO_COLLISION, RULE_COLLISION, PRINCIPLE_COLLISION,
    ROUTE_NONE, ROUTE_LEX_ORDERING, ROUTE_BALANCING,
)

# source_topology — jurisdiction conflict-ordering regime → pack (O144)
from .source_topology import (
    HIERARCHICAL, PLURAL, HORIZONTAL, REGIMES, SourceTopology,
    REGIME_PACKS, TOPOLOGIES, JUS_COGENS_PACK, pack_for, topology_for,
)

# canons — interpretive canon-set registry per legal family (O147)
from .canons import (
    CanonSet, CIVIL_LAW, COMMON_LAW, USUL_AL_FIQH, US_TEXTUALIST,
    CANON_SETS, FAMILIES, canon_set_for, tiebreaker_for,
)

# dedup — candidate deduplication / merge (O16)
from .dedup import CanonicalKey, MergeGroup, DedupResult, canonical_key, dedup

# nested_exceptions — exception-to-exception (Rückausnahme) recursion (O58)
from .nested_exceptions import (
    ExceptionNode, NodeEval, ExceptionVerdict, evaluate_exceptions, blocks,
)

# norm_construction — [I]-tier harness: Normtext → grounded Rule | ESCALATE (O26)
from .norm_construction import (
    Element, NormProposal, ConstructionResult, construct_norm,
)

# auslegung — [I]-tier harness: per-element interpretation via the canons (O36–O45)
from .auslegung import ReadingResult, canon_prompt, interpret_element

# precedent_ratio — [I]-tier harness: case-text → ratio (obiter excluded) | ESCALATE (O143)
from .precedent_ratio import (
    RatioElement, RatioProposal, RatioResult, extract_ratio,
)

# phases — Gutachtenstil phase ordering + briefs (presentation; host-parity surface)
from .phases import PHASE_ORDER, brief, curriculum, all_briefs

# structural_construction — [I]-tier factual harness: text → ontology (Dimension.STRUCTURAL) | ESCALATE
from .structural_construction import (
    Concept, HierarchyEdge, StructuralResult, construct_structure,
)

# causal_construction — [I]-tier factual harness: text → causal model (Dimension.CAUSAL) | ESCALATE
from .causal_construction import (
    STATED, PRESUPPOSED, CausalClaim, PresupposedLink, CausalResult, construct_causal,
)

# temporal_construction — [I]-tier factual harness: text → procedure + deadlines (Dimension.TEMPORAL) | ESCALATE
# (deadlines built on temporal.RelativeDeadline/Duration; renewal/option/term → renewal_construction, Loop 14b)
from .temporal_construction import (
    TemporalResult, FlaggedDeadline, construct_temporal,
)

# renewal_construction — [I]-tier temporal extension: text → term + renewal (auto/option) + reversion
# (built on the existing temporal.RenewalRule/Term/Duration — consumed, not re-grown; ambiguous kind → escalate)
from .renewal_construction import (
    RenewalResult, NoticeFlag, ReversionFlag, construct_renewal,
)

# relational_construction — [I]-tier factual harness: text → roles + relations (Dimension.RELATIONAL) | ESCALATE
# (composition via relation.RelationAlgebra; Hohfeld correlativity via deontic.correlative — both consumed, not re-grown)
from .relational_construction import (
    Role, CorrelativePosition, RelationalResult, construct_relational,
)

# cross_subsumption — [D] cross-dimensional subsumption: route a norm condition to its dimension evaluator
# (consumes subsumption.holds + dimensions + RelationAlgebra; incomplete/presupposed fact → OPEN, never SATISFIED)
from .cross_subsumption import (
    Verdict, Condition, FactSpace, DimVerdict, AntecedentVerdict,
    subsume_across, subsume_antecedent, fold_verdicts,
)

# grading — [D] the contract-grader: score a harness run (terminal + provenance + warrant + floor + signed-replay);
# rewards correct ESCALATE, punishes confident fabrication; harvests only passing runs (grade_harvest → datapump)
# (harvest re-exported as grade_harvest to avoid colliding with datapump.harvest)
from .grading import (
    Terminal, GradeReport, terminal_of, grade_run, harvest as grade_harvest,
)

# issue_aggregation — [D] cross-issue aggregation: combine sub-issue verdicts, any OPEN dominates (O112)
from .issue_aggregation import IssueAggregate, aggregate_issues

# gap_fork — [I]-tier Rechtsfortbildung harness: gap classify + analogy / e-contrario /
# a-fortiori / teleological move; Wortlautgrenze or contra-legem → ESCALATE (O63–O74)
from .gap_fork import (
    GapResult, GapProposal, resolve_gap, Element as GapElement,
)

# standard_eval — [I]-tier open-standard harness: reasonable-person / good-faith applied
# to facts against a constructed benchmark; genuinely-contested → ESCALATE (O146)
from .standard_eval import (
    StandardResult, StandardProposal, evaluate_standard, Element as StandardElement,
)

# quantitative — [D] evaluator for numeric antecedent conditions: threshold + interval
# membership over unit-carrying quantities; missing/mismatched operand → OPEN (evaluates
# the predicate.Predicate that `predicate` parses; returns the shared DimVerdict)
from .quantitative import (
    evaluate_quantitative, QuantCondition, Interval, QuantError,
)

# definition_closure — [D] transitively expand a defined term through injected
# definitional edges (closure via reasoning.compose_paths + RelationAlgebra.compose_path
# chain-coherence); a definitional cycle or a contested chain → open=True, never a
# fabricated complete definition (O-DEFCLOSURE)
from .definition_closure import ClosedDefinition, close_definition

# epistemic_status — [D] tagging+propagation LAYER over the shared OPEN vocabulary:
# settled (asserted/inferred) vs unsettled (presupposed/contested/unknown); weakest-link
# via aggregate_issues → any unsettled premise makes the conclusion OPEN, never SATISFIED
from .epistemic_status import (
    EpistemicStatus, SETTLED, UNSETTLED, is_settled, is_unsettled,
    status_to_verdict, StatusedPremise,
    propagate_premises, propagate_under_condition, propagate_derivation,
    RootCauseReport, root_causes,
)
from .oversight import BriefItem, OversightBrief, oversight_brief
from .divergence import (
    Mandate, TrajectoryStep, Divergence, detect, fold_divergences,
)
from .collapse import ConstituentState, Constituent, state_to_verdict, collapse
from .falsifiability import (
    Falsifiability, SUPPORT_FLOOR, Evidence,
    rank, best_support, support_verdict, fold_support,
)
from .escalation import (
    Ladder, Factor, Escalation,
    ceiling, autonomy_verdict, fold_autonomy, relax,
)
from .proxy import (
    Movement, Proxy, Substitution, ProxyCycle,
    check_proxies, chain, fold_substitutions,
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
    "Neighborhood", "neighborhood", "to_undirected",
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
    # closure — deontic permissive/prohibitive closure with polarity (O140)
    "AgentMode", "ClosureResult", "close", "is_strong_permission", "verdict_to_operator",
    # consistency — universalizability / treat-like-alike (O151)
    "DecidedCase", "InconsistentPair", "ConsistencyReport",
    "check_consistency", "check_nondiscrimination", "terminal_state",
    "decided_case_from_record",
    # burden — burden / presumption / standard-of-proof + non-liquet (O102–O105, O107)
    "Standard", "STANDARDS", "meets",
    "Element", "Presumption", "ElementFinding", "BurdenReport", "allocate",
    # distribution — inequality + adverse-impact instrumentation (O148, O152)
    "FOUR_FIFTHS", "InequalityMetrics", "inequality",
    "ImpactRatio", "adverse_impact", "rates_from_cases",
    # justice_screen — anti-blindness value/justice screen, flag-only (O154 formal)
    "ScreenResult", "TrippedReason", "justice_screen",
    "INCONSISTENCY", "DISCRIMINATION", "ADVERSE_IMPACT",
    # welfare — welfare functions + Pareto/fair-division, compute-only (O149, O150)
    "WELFARE_PRINCIPLES", "UTILITARIAN", "RAWLSIAN", "PRIORITARIAN", "EGALITARIAN",
    "WelfareEvaluation", "welfare_evaluate",
    "ParetoReport", "pareto_allocations", "FairDivisionReport", "fair_division",
    # proportionality — Verhältnismäßigkeit + Weight Formula, tie→ESCALATE (O94–O99)
    "proportionality", "ProportionalityResult", "PrincipleWeight", "Alternative",
    "ProngVerdict", "weight_formula", "necessity_holds", "TRIAD", "LIGHT", "MODERATE", "SERIOUS",
    # principles — collision-of-principles detection + routing (O93)
    "classify_collision", "route_for", "CollisionRouting",
    "RULE", "PRINCIPLE", "NO_COLLISION", "RULE_COLLISION", "PRINCIPLE_COLLISION",
    "ROUTE_NONE", "ROUTE_LEX_ORDERING", "ROUTE_BALANCING",
    # source_topology — jurisdiction conflict-ordering regime → pack (O144)
    "HIERARCHICAL", "PLURAL", "HORIZONTAL", "REGIMES", "SourceTopology",
    "REGIME_PACKS", "TOPOLOGIES", "JUS_COGENS_PACK", "pack_for", "topology_for",
    # canons — interpretive canon-set registry per legal family (O147)
    "CanonSet", "CIVIL_LAW", "COMMON_LAW", "USUL_AL_FIQH", "US_TEXTUALIST",
    "CANON_SETS", "FAMILIES", "canon_set_for", "tiebreaker_for",
    # dedup — candidate deduplication / merge (O16)
    "CanonicalKey", "MergeGroup", "DedupResult", "canonical_key", "dedup",
    # nested_exceptions — exception-to-exception (Rückausnahme) recursion (O58)
    "ExceptionNode", "NodeEval", "ExceptionVerdict", "evaluate_exceptions", "blocks",
    # [I]-tier harnesses — model fills, contract gates, escalate-the-open
    "Element", "NormProposal", "ConstructionResult", "construct_norm",     # O26
    "ReadingResult", "canon_prompt", "interpret_element",                   # O36–O45
    "RatioElement", "RatioProposal", "RatioResult", "extract_ratio",        # O143
    # phases — Gutachtenstil phase ordering + briefs (host-parity surface)
    "PHASE_ORDER", "brief", "curriculum", "all_briefs",
    # structural_construction — [I]-tier factual harness (Dimension.STRUCTURAL)
    "Concept", "HierarchyEdge", "StructuralResult", "construct_structure",
    # causal_construction — [I]-tier factual harness (Dimension.CAUSAL)
    "STATED", "PRESUPPOSED", "CausalClaim", "PresupposedLink", "CausalResult", "construct_causal",
    # temporal_construction — [I]-tier factual harness (Dimension.TEMPORAL)
    "TemporalResult", "FlaggedDeadline", "construct_temporal",
    # renewal_construction — [I]-tier temporal extension (temporal.RenewalRule/Term)
    "RenewalResult", "NoticeFlag", "ReversionFlag", "construct_renewal",
    # relational_construction — [I]-tier factual harness (Dimension.RELATIONAL)
    "Role", "CorrelativePosition", "RelationalResult", "construct_relational",
    # cross_subsumption — [D] cross-dimensional subsumption (route condition → dimension evaluator)
    "Verdict", "Condition", "FactSpace", "DimVerdict", "AntecedentVerdict",
    "subsume_across", "subsume_antecedent", "fold_verdicts",
    # grading — [D] the contract-grader (rewards ESCALATE, punishes fabrication)
    "Terminal", "GradeReport", "terminal_of", "grade_run", "grade_harvest",
    # issue_aggregation — [D] cross-issue aggregation (any OPEN dominates)
    "IssueAggregate", "aggregate_issues",
    # gap_fork — [I]-tier Rechtsfortbildung (Wortlautgrenze / contra-legem → ESCALATE)
    "GapResult", "GapProposal", "resolve_gap", "GapElement",
    # standard_eval — [I]-tier open-standard (genuinely-contested → ESCALATE)
    "StandardResult", "StandardProposal", "evaluate_standard", "StandardElement",
    # quantitative — [D] numeric antecedent evaluator (threshold + interval; OPEN on gap)
    "evaluate_quantitative", "QuantCondition", "Interval", "QuantError",
    # definition_closure — [D] transitive definitional expansion (cycle/contested → open)
    "ClosedDefinition", "close_definition",
    # epistemic_status — [D] settled/unsettled premise layer (unsettled → OPEN, weakest-link)
    "EpistemicStatus", "SETTLED", "UNSETTLED", "is_settled", "is_unsettled",
    "status_to_verdict", "StatusedPremise",
    "propagate_premises", "propagate_under_condition", "propagate_derivation",
    "RootCauseReport", "root_causes",
    # oversight — the bounded brief (selects; decides nothing)
    "BriefItem", "OversightBrief", "oversight_brief",
    # divergence — a trajectory compared against the purpose it was given
    "Mandate", "TrajectoryStep", "Divergence", "detect", "fold_divergences",
    # collapse — a conjunction where any term at its floor collapses the whole
    "ConstituentState", "Constituent", "state_to_verdict", "collapse",
    # falsifiability — rank evidence by how it could be shown wrong
    "Falsifiability", "SUPPORT_FLOOR", "Evidence",
    "rank", "best_support", "support_verdict", "fold_support",
    # escalation — autonomy as a ceiling several factors impose, never a score
    "Ladder", "Factor", "Escalation",
    "ceiling", "autonomy_verdict", "fold_autonomy", "relax",
    # proxy — what a measurement stands for, and whether anyone checked
    "Movement", "Proxy", "Substitution", "ProxyCycle",
    "check_proxies", "chain", "fold_substitutions",
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
