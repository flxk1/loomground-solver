# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Panel core — the shared vocabulary a graded-panel case is authored against.

This module holds the pieces every case and every stage share, and it holds
**no** grading or evaluation logic of its own: it *reuses* the engine's own
vocabulary rather than minting a parallel one.

  * :class:`grading.Terminal` — the four terminal classes a run resolves to
    (DETERMINATE / NOT_MET / ESCALATE / RESIDUAL). ``OPEN`` (the node-level
    escalate verdict) maps onto ``ESCALATE`` at the case level, exactly as
    :func:`grading.terminal_of` already maps it.
  * :class:`cross_subsumption.Verdict` — the three-valued **node-level** verdict
    (SATISFIED / NOT_SATISFIED / OPEN). ``OPEN`` is a *first-class PASS*, not a
    failure to decide: a node correctly returning OPEN is the honest answer when
    the fact is presupposed, contested, or unclassifiable. This module never
    defines a parallel three-valued type (the conformance gate forbids it).
  * :class:`dimensions.Dimension` — the five factual/normative dimensions, plus
    the string tag ``"nD"`` for governance meta-norms (which has no
    :class:`~dimensions.Dimension` member).
  * :class:`epistemic_status.EpistemicStatus` — how *settled* a premise is.

A **Stage** is one evaluable node of a case: a claim the runner drives through a
REAL solver evaluator to a :class:`~cross_subsumption.Verdict`. Every stage
carries its own :class:`Grounding` — a span-ref (grounded) XOR an ``incomplete``
marker (honestly presupposed-but-not-stated) — so §8.1(c)'s honest-open channel
is enforced per node, universally, for statutes, contracts and policies alike.

Pure stdlib beyond the solver package. No ``loomground_legal`` /
``loomground_versum`` import.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# Reused engine vocabulary — imported here so authors get one import surface and
# the panel never re-declares any of it.
from ...cross_subsumption import Verdict
from ...dimensions import Dimension
from ...epistemic_status import EpistemicStatus
from ...grading import Terminal

__all__ = [
    "Terminal", "Verdict", "Dimension", "EpistemicStatus",
    "CASE_KINDS", "SIMPLE_KINDS", "DIMENSION_TAGS", "ND",
    "Grounding", "StageOutcome", "Stage",
]


# ── discriminator + tag vocabularies ──────────────────────────────────────────

#: The case-kind discriminator. ``policy`` carries a STRUCTURED expectation (a
#: 5D+nD subgraph, §8.1); the others carry the SIMPLE expectation (one terminal
#: state · probes · expected warrants/provenance). ``moral`` is statute-shaped
#: for expectation purposes — a moral dilemma is graded on terminal + honesty,
#: not a subgraph.
CASE_KINDS: tuple[str, ...] = ("statute", "contract", "policy", "moral")

#: The kinds that use the SIMPLE expectation shape (everything but ``policy``).
SIMPLE_KINDS: frozenset = frozenset({"statute", "contract", "moral"})

#: ``"nD"`` — governance meta-norms — has no :class:`dimensions.Dimension`
#: member, so a node's dimension is a *string tag* drawn from the five dimension
#: values plus ``"nD"``.
ND = "nD"
DIMENSION_TAGS: frozenset = frozenset({d.value for d in Dimension} | {ND})


def _check_dimension_tag(tag: str) -> str:
    if tag not in DIMENSION_TAGS:
        raise ValueError(
            f"dimension tag {tag!r} is not one of {sorted(DIMENSION_TAGS)}")
    return tag


# ── grounding: the universal honest-open channel (H3, §8.1(c)) ────────────────

@dataclass(frozen=True)
class Grounding:
    """Where one claim/node is grounded — or an honest mark that it is *not*.

    Exactly one of ``span_ref`` / ``incomplete`` is set:

      * ``span_ref`` — the node is **grounded**: a source pinpoint / span id the
        claim rests on (e.g. ``"GDPR Art 33(1)"``). It becomes a *receipted
        ground* in the reasoning record.
      * ``incomplete`` — the node is **honestly incomplete**: the reason the
        policy/statute *presupposes* the fact but never states it (e.g.
        ``"breach occurrence is presupposed, never established"``). It becomes a
        recorded **gap** (coverage < 1.0), NEVER a fabricated sourced fact — and
        the grader **PASSES** it, by the same rule that passes a correct
        ESCALATE. This is §8.1(c)'s honest-open channel, made universal.

    ``ref`` names the claim/node this grounding is for (stable — it is the label
    carried into the record and the scorecard).
    """

    ref: str
    span_ref: Optional[str] = None
    incomplete: Optional[str] = None

    def __post_init__(self) -> None:
        has_span = bool((self.span_ref or "").strip())
        has_inc = bool((self.incomplete or "").strip())
        if has_span == has_inc:
            raise ValueError(
                f"grounding for {self.ref!r} needs exactly one of span_ref / "
                f"incomplete (got span_ref={self.span_ref!r}, "
                f"incomplete={self.incomplete!r})")

    @property
    def grounded(self) -> bool:
        """True iff this node rests on a real source span (not an honest gap)."""
        return bool((self.span_ref or "").strip())

    @classmethod
    def span(cls, ref: str, span_ref: str) -> "Grounding":
        return cls(ref=ref, span_ref=span_ref)

    @classmethod
    def gap(cls, ref: str, reason: str) -> "Grounding":
        return cls(ref=ref, incomplete=reason)


# ── stage outcome + the stage base ────────────────────────────────────────────

@dataclass(frozen=True)
class StageOutcome:
    """The verdict a stage computed, plus the trail that justifies it.

    ``verdict`` is the shared :class:`cross_subsumption.Verdict`. ``fact_text``
    is a short statement of the operative fact the stage turned on (used to
    assemble the reasoning record). ``evidence`` is the raw evaluator evidence
    (a path, a receipt, a comparison), retained for the trace / audit.
    """

    verdict: Verdict
    reason: str
    fact_text: str = ""
    evidence: Any = None


@dataclass(frozen=True, kw_only=True)
class Stage:
    """One evaluable node of a case — a claim driven through a REAL evaluator.

    Every concrete stage (see :mod:`loomground_solver.eval.panel.stages`) wraps
    exactly one solver operation (``subsume_across``, ``evaluate_quantitative``,
    ``evaluate_standard``, ``propagate_premises``, ``derive`` …) and returns a
    :class:`StageOutcome`. The runner never decides a node itself; it only folds
    the stages' verdicts through the engine's own OPEN-dominant aggregation.

    Common, kw-only fields carried by every stage:

      * ``name`` — the sub-issue key; stable, carried into the fold and the
        record.
      * ``grounding`` — this node's :class:`Grounding` (span-ref XOR incomplete).
      * ``warrant`` — the Toulmin warrant naming what licenses the move (becomes
        the record's chain-step warrant, so :func:`contract.check_warrants`
        passes).
      * ``dimension`` — a :data:`DIMENSION_TAGS` string (the five dimension
        values plus ``"nD"``).
    """

    name: str
    grounding: Grounding
    warrant: str
    dimension: str = Dimension.INTENTIONAL.value

    def __post_init__(self) -> None:
        _check_dimension_tag(self.dimension)
        if self.grounding.ref != self.name:
            # Keep the node id and its grounding ref aligned — the record and the
            # scorecard are keyed by name.
            object.__setattr__(self, "grounding",
                               _rekey(self.grounding, self.name))

    def evaluate(self) -> StageOutcome:  # pragma: no cover - abstract
        raise NotImplementedError("concrete stages implement evaluate()")


def _rekey(g: Grounding, ref: str) -> Grounding:
    return Grounding(ref=ref, span_ref=g.span_ref, incomplete=g.incomplete)
