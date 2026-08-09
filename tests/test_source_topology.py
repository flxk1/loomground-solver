# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""O144 — source-topology selection: a jurisdiction's ordering REGIME selects
which resolution pack applies. The regime, not the two norms alone, decides how
a collision is resolved — and where the source topology offers no honest
ordering, the pack must ESCALATE rather than fabricate one."""
from __future__ import annotations

from types import SimpleNamespace

from loomground_solver import GENERIC_PACK, LEX_CONFLICT_PACK, RulePack
from loomground_solver.scenario import Scenario, Norm, derive
from loomground_solver.source_topology import (
    HIERARCHICAL, PLURAL, HORIZONTAL, REGIMES,
    JUS_COGENS_PACK, REGIME_PACKS, TOPOLOGIES,
    pack_for, topology_for,
)


def _norm(peremptory: int):
    """A minimal norm-like object carrying the peremptory marker the horizontal
    pack orders on (RulePack.resolve reads it via getattr)."""
    return SimpleNamespace(deontic="prohibited", peremptory=peremptory)


# ── hierarchical regime routes to the classical defeater pack ────────────────

def test_hierarchical_regime_selects_lex_conflict_pack():
    assert pack_for(HIERARCHICAL) is LEX_CONFLICT_PACK
    # and it really does resolve on rank (lex superior) — not our job to re-test
    # resolution, but confirm the wiring reaches a separating pack.
    assert topology_for(HIERARCHICAL).escalates_ordinary_conflicts is False


# ── plural regime MUST escalate a genuine collision (the honesty floor) ───────

def test_plural_regime_selects_generic_pack_and_escalates():
    pack = pack_for(PLURAL)
    assert pack is GENERIC_PACK
    # end-to-end: two contradictory ordinary norms, no meta-ordering -> OPEN.
    sc = Scenario("plural-world", norms=[
        Norm("share-data", "obligatory", source="state-order"),
        Norm("share-data", "prohibited", source="customary-order"),
    ])
    r = derive(sc, pack=pack).resolution_for("share-data")
    assert r.status == "open" and r.verdict is None
    assert ("customary-order", "state-order") in [tuple(sorted(c)) for c in r.collisions]
    # never fabricates an ordering: the pack itself separates nothing.
    assert GENERIC_PACK.orderings == ()


# ── horizontal regime: jus cogens on top, everything else escalates ──────────

def test_horizontal_regime_jus_cogens_defeats_ordinary_norm():
    pack = pack_for(HORIZONTAL)
    assert pack is JUS_COGENS_PACK
    assert isinstance(pack, RulePack)          # built by CONSUMING the pack machinery
    peremptory, ordinary = _norm(1), _norm(0)
    # the peremptory norm wins over the ordinary one …
    assert pack.resolve(peremptory, ordinary) == "a"
    assert pack.resolve(ordinary, peremptory) == "b"
    assert pack.separating_rule(peremptory, ordinary) == "jus-cogens"


def test_horizontal_regime_ordinary_conflicts_escalate():
    pack = pack_for(HORIZONTAL)
    # two ordinary norms: no hierarchy among equals -> no winner -> escalate.
    assert pack.resolve(_norm(0), _norm(0)) is None
    # even two peremptory norms in conflict do not auto-resolve (genuine clash).
    assert pack.resolve(_norm(1), _norm(1)) is None
    assert topology_for(HORIZONTAL).escalates_ordinary_conflicts is True


# ── registry integrity + unknown-regime discipline ───────────────────────────

def test_registry_covers_exactly_the_declared_regimes():
    assert set(REGIME_PACKS) == set(REGIMES) == set(TOPOLOGIES)
    for regime in REGIMES:
        assert topology_for(regime).pack is REGIME_PACKS[regime]


def test_unknown_regime_raises_never_fabricates_an_ordering():
    for bad in ("", "monist", "feudal", "HIERARCHICAL "):
        try:
            pack_for(bad)
        except KeyError:
            continue
        raise AssertionError(f"expected KeyError for regime {bad!r}")
