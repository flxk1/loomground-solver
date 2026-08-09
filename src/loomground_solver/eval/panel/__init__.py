# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The graded panel — the permanent, repeatable harness that runs the legal /
normative reasoning pipeline over statutes, contracts and policies and grades
each run by the reasoning contract (DoD §4.4–§4.6, §8.1).

One import surface for the whole fleet:

  * author a case → :class:`CaseSpec` (discriminated by ``case_kind``), built
    from :mod:`stages` nodes each carrying a :class:`Grounding`;
  * run + grade a case → :func:`run_case` → :class:`CaseResult` (contract
    scorecard + signed-replay/provenance artifacts);
  * discover the corpus → :func:`collect_cases` (drop a file in ``cases/``).

The harness *consumes* the engine — :func:`grading.grade_run`, the
:class:`cross_subsumption.Verdict` vocabulary, the real dimension evaluators —
and reimplements none of it. It rewards a correct ESCALATE / OPEN and fails a
confident fabrication by construction.
"""
from __future__ import annotations

from .case_spec import (
    CaseSpec, NodeExpectation, PROBE_KINDS, PresupposedProbe, Probe,
    UnderstandBar,
)
from .core import (
    CASE_KINDS, DIMENSION_TAGS, EpistemicStatus, Grounding, Stage, StageOutcome,
    Terminal, Verdict,
)
from .registry import collect_cases, collect_cases_by_kind, discover_case_modules
from .runner import CaseResult, ProbeResult, StageResult, run_case, run_stages
from .stages import (
    DeonticResolution, EpistemicPremise, HonestGap, IntentionalCondition,
    QuantThreshold, StandardApplication, StructuralCondition, TemporalOrder,
    duration, is_a, money,
)

__all__ = [
    # schema
    "CaseSpec", "Probe", "PROBE_KINDS", "NodeExpectation", "UnderstandBar",
    "PresupposedProbe", "Grounding", "Stage", "StageOutcome",
    "Terminal", "Verdict", "EpistemicStatus", "CASE_KINDS", "DIMENSION_TAGS",
    # stages
    "IntentionalCondition", "StructuralCondition", "TemporalOrder",
    "QuantThreshold", "StandardApplication", "EpistemicPremise",
    "DeonticResolution", "HonestGap", "is_a", "money", "duration",
    # runner
    "run_case", "run_stages", "CaseResult", "StageResult", "ProbeResult",
    # registry
    "collect_cases", "collect_cases_by_kind", "discover_case_modules",
]
