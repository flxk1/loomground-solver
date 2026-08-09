# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""CaseSpec — the frozen, discriminated schema one panel case is authored to.

A :class:`CaseSpec` describes one case the graded panel runs: the input, the
question, the REAL-evaluator stages that compute its verdict, the adversarial
probes it must survive, and the *expectation* it is graded against. The schema
is **discriminated by** ``case_kind``:

  * ``statute`` / ``contract`` / ``moral`` — the **SIMPLE** expectation: one
    correct terminal state, its probes, and the expected per-dimension grade
    (warrants / provenance / floor / replay).
  * ``policy`` — the **STRUCTURED** expectation (§8.1): a 5D+nD subgraph, a
    definition-closure map, the six-answer understand-bar, and presupposed-fact
    probes — *in addition* to a case-level terminal.

**Universal fields hold for all three kinds**, because H3 ("fabrication rate 0")
is universal:

  * every stage carries a :class:`core.Grounding` — ``span_ref`` (grounded) XOR
    ``incomplete`` (honestly presupposed-but-not-stated); the grader PASSES a
    correctly-``incomplete`` node by the same rule that passes a correct
    ESCALATE;
  * the node-level verdict vocabulary is :class:`cross_subsumption.Verdict`
    with **OPEN a first-class PASS** — never a parallel enum.

The runner (:mod:`loomground_solver.eval.panel.runner`) *computes* the case's
terminal from the stages' verdicts (folded through the engine's own OPEN-dominant
aggregation) and *grades* it against the expectation — it never hand-sets the
terminal to match. Authoring a case is: pick a kind, write the stages, declare
the honest expectation.

No ``loomground_legal`` / ``loomground_versum`` import.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from .core import (
    CASE_KINDS, SIMPLE_KINDS, DIMENSION_TAGS, Grounding, Stage, Terminal, Verdict,
)

__all__ = [
    "CaseSpec", "Probe", "NodeExpectation", "UnderstandBar", "PresupposedProbe",
    "PROBE_KINDS",
]


# ── probe vocabulary ──────────────────────────────────────────────────────────

#: The adversarial probe markers a case may declare. Each names a way an input
#: tempts fabrication; the honest outcome of every one is ESCALATE / OPEN.
PROBE_KINDS: frozenset = frozenset({
    "hidden_exception",     # a carve-out the norm's own text carries but hides
    "genuine_collision",    # two contradictory norms, no ordering → escalate
    "contra_legem",         # a reading past the Wortlautgrenze / plain meaning
    "presupposed_fact",     # a world-fact the norm assumes but never establishes
    "unsettled_reading",    # a plausible-but-contested interpretation
})


def _as_terminal(value) -> Terminal:
    """Coerce to a :class:`grading.Terminal`; ``OPEN`` maps to ``ESCALATE``."""
    if isinstance(value, Terminal):
        return value
    tok = str(getattr(value, "value", value)).strip().lower()
    if tok == "open":
        return Terminal.ESCALATE
    for t in Terminal:
        if t.value == tok or t.name.lower() == tok:
            return t
    raise ValueError(f"unknown terminal {value!r}")


@dataclass(frozen=True)
class Probe:
    """One adversarial probe: a sub-bundle of REAL stages whose honest fold must
    reach ``expected`` (ESCALATE / OPEN — coerced to :class:`Terminal`).

    ``kind`` is one of :data:`PROBE_KINDS`. The probe is *run* — its ``stages``
    are evaluated and folded exactly like the main case — so "it escalates" is
    proven, not asserted. A probe passes iff its computed terminal equals
    ``expected``.
    """

    kind: str
    stages: Tuple[Stage, ...]
    expected: Terminal = Terminal.ESCALATE
    note: str = ""

    def __post_init__(self) -> None:
        if self.kind not in PROBE_KINDS:
            raise ValueError(
                f"probe kind {self.kind!r} not in {sorted(PROBE_KINDS)}")
        object.__setattr__(self, "expected", _as_terminal(self.expected))
        if self.expected not in (Terminal.ESCALATE, Terminal.RESIDUAL):
            raise ValueError(
                "an adversarial probe's honest outcome must be ESCALATE (or "
                f"RESIDUAL), never {self.expected.value} — that would reward "
                "the fabrication the probe exists to catch")
        if not self.stages:
            raise ValueError(f"probe {self.kind!r} has no stages to evaluate")


# ── policy-only structured expectation (§8.1) ─────────────────────────────────

@dataclass(frozen=True)
class NodeExpectation:
    """One node of a policy's expected 5D+nD subgraph.

    ``dimension`` is a :data:`core.DIMENSION_TAGS` string (the five dimensions
    plus ``"nD"``); ``node`` is the node id; ``expected_verdict`` is the shared
    :class:`cross_subsumption.Verdict` this node should compute to — **OPEN is a
    valid, PASSING expectation** (a presupposed node correctly returning OPEN).
    """

    dimension: str
    node: str
    expected_verdict: Verdict

    def __post_init__(self) -> None:
        if self.dimension not in DIMENSION_TAGS:
            raise ValueError(
                f"node {self.node!r} dimension {self.dimension!r} not in "
                f"{sorted(DIMENSION_TAGS)}")
        if not isinstance(self.expected_verdict, Verdict):
            object.__setattr__(self, "expected_verdict",
                               Verdict(str(self.expected_verdict).lower()))


@dataclass(frozen=True)
class UnderstandBar:
    """The §8.1 six-answer understand-bar — what a policy must let the layer
    answer, grounded or honestly-open. Each field is the expected grounded
    answer (or the honest ``"OPEN: …"`` marker where the policy presupposes it).
    """

    who_what: str = ""
    conditions: str = ""
    consequence: str = ""
    procedure: str = ""
    purpose: str = ""
    gaps: str = ""


@dataclass(frozen=True)
class PresupposedProbe:
    """A §8.1(d) presupposed-fact probe: ``target`` is the world-fact the policy
    assumes but never states; ``expected`` is its honest outcome (OPEN /
    ESCALATE). The layer must never fabricate the world-model the policy
    presupposes."""

    target: str
    expected: Terminal = Terminal.ESCALATE

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected", _as_terminal(self.expected))


# ── the case spec ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CaseSpec:
    """One graded-panel case — discriminated by ``case_kind``.

    UNIVERSAL fields (all kinds):

      * ``id`` — stable case id (unique across the registry).
      * ``title`` — human title.
      * ``case_kind`` — the discriminator: ``statute`` | ``contract`` |
        ``policy`` | ``moral`` (``moral`` uses the SIMPLE expectation shape).
      * ``source_text`` — the norm / clause / policy text (or a path to it).
      * ``question`` — what is asked.
      * ``stages`` — the REAL-evaluator nodes the runner computes and folds; each
        carries its own :class:`core.Grounding` (span-ref XOR incomplete).
      * ``expected_terminal`` — the correct case-level terminal (DETERMINATE /
        NOT_MET / RESIDUAL / ESCALATE; ``OPEN`` is coerced to ESCALATE).
      * ``probes`` — adversarial probes; each must compute to ESCALATE.
      * ``tempting_answer`` — the confident DETERMINATE answer the input tempts
        (used by ``run_case(spec, tempted=True)`` to prove the grader FAILS a
        fabrication and does not harvest it).
      * ``stake`` / ``personal`` / ``oversight_level`` — judgment-floor inputs
        forwarded to :func:`grading.grade_run` (default: low-stakes autonomous).

    SIMPLE-kind fields (``statute`` / ``contract`` / ``moral``):

      * ``expected_grade`` — the per-dimension grade the scorecard should show
        (keys: ``terminal`` ``provenance`` ``warrant`` ``floor`` ``replay``);
        omitted keys default to ``True``.
      * ``residual_options`` — for a RESIDUAL case, the ≥2 bounded options.

    POLICY-kind fields (``policy`` only) — the §8.1 STRUCTURED expectation:

      * ``expected_subgraph`` — per-node :class:`NodeExpectation`s (5D+nD).
      * ``definition_closure`` — ``{term -> "resolves_to_primitives" | "OPEN"}``;
        an ``OPEN`` term with a truthful unresolved marker is a **PASS** (honest
        gap-surfacing — recursive closure is NEEDS-BUILDING per §8.2).
      * ``understand_bar`` — the six-answer :class:`UnderstandBar`.
      * ``presupposed_probes`` — §8.1(d) :class:`PresupposedProbe`s.
    """

    # — universal —
    id: str
    title: str
    case_kind: str
    source_text: str
    question: str
    stages: Tuple[Stage, ...]
    expected_terminal: Terminal
    probes: Tuple[Probe, ...] = ()
    tempting_answer: str = ""
    stake: bool = False
    personal: bool = False
    oversight_level: str = "autonomous"

    # — simple-kind expectation —
    expected_grade: Mapping[str, bool] = field(default_factory=dict)
    residual_options: Tuple[str, ...] = ()

    # — policy-kind structured expectation (§8.1) —
    expected_subgraph: Tuple[NodeExpectation, ...] = ()
    definition_closure: Mapping[str, str] = field(default_factory=dict)
    understand_bar: Optional[UnderstandBar] = None
    presupposed_probes: Tuple[PresupposedProbe, ...] = ()

    def __post_init__(self) -> None:
        if self.case_kind not in CASE_KINDS:
            raise ValueError(
                f"case_kind {self.case_kind!r} not in {sorted(CASE_KINDS)}")
        object.__setattr__(self, "expected_terminal",
                           _as_terminal(self.expected_terminal))
        object.__setattr__(self, "stages", tuple(self.stages))
        object.__setattr__(self, "probes", tuple(self.probes))
        if not self.stages:
            raise ValueError(f"case {self.id!r} has no stages")
        # node-name uniqueness — the fold and the scorecard are keyed by name.
        names = [s.name for s in self.stages]
        if len(set(names)) != len(names):
            raise ValueError(f"case {self.id!r} has duplicate stage names: {names}")
        if self.expected_terminal is Terminal.RESIDUAL and \
                len(self.residual_options) < 2:
            raise ValueError(
                f"case {self.id!r} expects RESIDUAL but names < 2 options")
        # discriminator: only policy carries the structured section.
        if self.is_policy:
            if not self.expected_subgraph:
                raise ValueError(
                    f"policy case {self.id!r} needs an expected_subgraph (§8.1)")
        else:
            if self.expected_subgraph or self.definition_closure \
                    or self.understand_bar or self.presupposed_probes:
                raise ValueError(
                    f"{self.case_kind} case {self.id!r} carries policy-only "
                    "structured fields — those belong to case_kind='policy'")

    @property
    def is_policy(self) -> bool:
        return self.case_kind == "policy"

    @property
    def is_simple(self) -> bool:
        return self.case_kind in SIMPLE_KINDS

    @property
    def grounding(self) -> Tuple[Grounding, ...]:
        """The per-node grounding of the whole case — the aggregate of every
        stage's :class:`core.Grounding` (the universal honest-open ledger)."""
        return tuple(s.grounding for s in self.stages)
