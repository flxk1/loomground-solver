# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Source-topology selection (O144) — pick the conflict-resolution pack that a
jurisdiction's *ordering regime* licenses.

WHICH rule-pack resolves a normative collision is not a property of the two
norms alone: it depends on how the legal order they inhabit is *arranged*. Three
arrangements recur across systems, and each licenses a different pack — all of
them already published (or buildable) in :mod:`loomground_solver.rulepacks`.
This module is a pure **selector**; it consumes the pack machinery, it never
re-implements resolution.

  * ``HIERARCHICAL`` — a stepped order (Kelsen's *Stufenbau*): lex superior ▷
    specialis ▷ posterior. Selects :data:`rulepacks.LEX_CONFLICT_PACK`.
  * ``PLURAL`` — coexisting, un-unified orders with **no meta-ordering** to rank
    them (legal pluralism: overlapping state / customary / religious orders).
    There is no honest winner to compute, so every genuine contradiction must
    ESCALATE. Selects :data:`rulepacks.GENERIC_PACK` (empty orderings ⇒ nothing
    auto-resolves). Fabricating an ordering here would be a lie about the source
    topology; the honesty floor forbids it.
  * ``HORIZONTAL`` — a consent-based order of formal equals (classical public
    international law): no hierarchy among ordinary norms, with the single
    exception of *jus cogens* / peremptory norms, which sit above the rest. This
    is expressed by :data:`JUS_COGENS_PACK`, built here from the SAME
    :class:`rulepacks.Ordering` / :class:`rulepacks.RulePack` primitives: one
    ordering on a ``peremptory`` marker, and otherwise — like the plural regime —
    an escalation. A peremptory norm defeats an ordinary one; two ordinary norms
    (or two peremptory norms) in contradiction escalate.

The module does not resolve anything itself and holds no jurisdiction table:
give it a regime, it hands back the pack. Deterministic, pure stdlib.
"""
from __future__ import annotations

from dataclasses import dataclass

from .rulepacks import GENERIC_PACK, LEX_CONFLICT_PACK, Ordering, RulePack


# ── regime constants — the three source topologies ───────────────────────────

HIERARCHICAL = "hierarchical"   # Stufenbau: lex superior ▷ specialis ▷ posterior
PLURAL = "plural"               # coexisting orders, no meta-ordering ⇒ escalate
HORIZONTAL = "horizontal"       # consent-based equals; only jus cogens on top

REGIMES: tuple[str, ...] = (HIERARCHICAL, PLURAL, HORIZONTAL)


# ── the horizontal / consent-based pack, built from the pack primitives ──────
#: The single ordering the horizontal regime recognises: a peremptory (jus
#: cogens) marker outranks an ordinary norm. Norms carry ``peremptory`` = 1 for
#: a peremptory norm, 0 (the default via ``getattr(..., 0)``) otherwise.
PEREMPTORY_ORDERING = Ordering("jus-cogens", "peremptory")

#: Public-international-law topology: no hierarchy among ordinary norms; a single
#: peremptory marker sits on top; everything else escalates. Built by CONSUMING
#: :class:`rulepacks.RulePack` / :class:`rulepacks.Ordering`, not by re-coding
#: resolution — an empty separation beyond the peremptory marker yields ``None``
#: from ``RulePack.resolve``, i.e. a genuine, non-auto-resolvable collision.
JUS_COGENS_PACK = RulePack(
    "jus-cogens",
    orderings=(PEREMPTORY_ORDERING,),
    frame="deontic",
)


# ── the regime → pack registry + selector ────────────────────────────────────

REGIME_PACKS: dict[str, RulePack] = {
    HIERARCHICAL: LEX_CONFLICT_PACK,
    PLURAL: GENERIC_PACK,
    HORIZONTAL: JUS_COGENS_PACK,
}


@dataclass(frozen=True)
class SourceTopology:
    """A named source-topology regime and the resolution pack it licenses.

    A thin, inspectable record for a registry surface: the regime name, the
    pack it selects, whether ordinary contradictions auto-resolve under it, and
    a human note. The pack is the operative part; the flags are provenance."""
    regime: str
    pack: RulePack
    escalates_ordinary_conflicts: bool
    note: str = ""


#: Registry of the three regimes with provenance. ``escalates_ordinary_conflicts``
#: is True wherever two ordinary (non-privileged) contradictory norms cannot be
#: separated by the selected pack — the honesty floor made explicit.
TOPOLOGIES: dict[str, SourceTopology] = {
    HIERARCHICAL: SourceTopology(
        HIERARCHICAL, LEX_CONFLICT_PACK, escalates_ordinary_conflicts=False,
        note="Stufenbau: lex superior ▷ specialis ▷ posterior; only a true tie escalates.",
    ),
    PLURAL: SourceTopology(
        PLURAL, GENERIC_PACK, escalates_ordinary_conflicts=True,
        note="Legal pluralism: no meta-ordering — every genuine contradiction escalates.",
    ),
    HORIZONTAL: SourceTopology(
        HORIZONTAL, JUS_COGENS_PACK, escalates_ordinary_conflicts=True,
        note="Consent-based equals: only jus cogens outranks; ordinary conflicts escalate.",
    ),
}


def pack_for(regime: str) -> RulePack:
    """Return the resolution :class:`rulepacks.RulePack` a source-topology regime
    licenses. Raises :class:`KeyError` on an unknown regime — an unrecognised
    topology is never silently mapped to a defeater order (the honesty floor:
    no fabricated ordering)."""
    try:
        return REGIME_PACKS[regime]
    except KeyError as exc:
        raise KeyError(
            f"unknown source-topology regime: {regime!r} (known: {REGIMES})"
        ) from exc


def topology_for(regime: str) -> SourceTopology:
    """Return the full :class:`SourceTopology` record (pack + provenance) for a
    regime. Raises :class:`KeyError` on an unknown regime."""
    try:
        return TOPOLOGIES[regime]
    except KeyError as exc:
        raise KeyError(
            f"unknown source-topology regime: {regime!r} (known: {REGIMES})"
        ) from exc
