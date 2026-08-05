# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The algebra of typed-relation composition — mechanism, not domain.

A dimensioned edge (see :mod:`loomground_solver.reasoning`) composes along the
*dimension* of a two-step chain. This module composes along the **relation
type** itself: given "A is connected to B by relation ``r1``, B to C by ``r2``",
what relation — if any — connects A to C?

That inference is an algebra with three deliberate outcomes, mirroring the
escalate-don't-guess discipline the rest of the solver enforces
(:class:`~loomground_solver.norm_contract.Level`, the grounded engine, the norm
contract):

* a **relation** — the chain has a settled composite;
* :data:`ESCALATE` — the chain is *contested*; surface the open question, never
  fabricate a resolution;
* ``None`` — nothing follows; the chain yields no relation at all.

The table is **partial on purpose**: only settled chains are filled. This class
is the domain-agnostic *mechanism* — it carries no vocabulary of its own. A
consuming plane supplies the relation vocabulary, the (partial) composition
table, the inverse map, and the relation→dimension map as **data**; the solver
never hardcodes anyone's relations. That is the same ports discipline the
package applies to governance and corpus: the engine here, the domain there.

Relation identifiers are any hashable token — a ``str`` or an ``Enum`` member —
so a legal plane can compose ``Connection`` members while another plane composes
plain strings, both over this one algebra.
"""
from __future__ import annotations

from typing import Any, Hashable, Iterable, Mapping, Optional, Tuple, Union

from .dimensions import Dimension


class _Escalate:
    """Sentinel for a *contested* composition — surface it, do not resolve it."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return "ESCALATE"


#: The single escalate-don't-guess marker for relation composition. A table maps
#: a contested two-step chain to this value; :meth:`RelationAlgebra.compose_path`
#: propagates it and flags the whole path as escalated.
ESCALATE = _Escalate()

#: A composed outcome: a relation identifier, :data:`ESCALATE`, or ``None``.
Composed = Union[Hashable, _Escalate, None]


class RelationAlgebra:
    """A partial composition algebra over a vocabulary of typed relations.

    Construct one from domain data; validation is fail-closed — a table or
    inverse map that names a relation outside ``vocabulary`` is a construction
    error, so a typo cannot silently degrade to "no inference". Lookups at
    reasoning time are lenient: an unknown pair composes to ``None`` (no relation
    follows) rather than raising, so noisy runtime data never crashes a walk.

    :meth:`compose_path` treats :data:`ESCALATE` as a checkpoint, not poison:
    when a step escalates, the fold restarts from the next leg (with the
    ``escalated`` flag latched) rather than voiding the whole chain, so the
    provenance of the legs beyond the contested step is still surfaced.
    """

    def __init__(
        self,
        *,
        vocabulary: Iterable[Hashable],
        table: Mapping[Tuple[Hashable, Hashable], Composed],
        inverses: Optional[Mapping[Hashable, Hashable]] = None,
        dimensions: Optional[Mapping[Hashable, Dimension]] = None,
        default_dimension: Dimension = Dimension.RELATIONAL,
    ) -> None:
        self.vocabulary: frozenset = frozenset(vocabulary)
        self.default_dimension = Dimension(default_dimension)

        bad: list[str] = []
        for (a, b), result in table.items():
            if a not in self.vocabulary or b not in self.vocabulary:
                bad.append(f"table key ({a!r}, {b!r}) uses an unknown relation")
            if result is not None and not isinstance(result, _Escalate) \
                    and result not in self.vocabulary:
                bad.append(f"table value {result!r} is an unknown relation")
        for src, dst in (inverses or {}).items():
            if src not in self.vocabulary or dst not in self.vocabulary:
                bad.append(f"inverse {src!r}->{dst!r} uses an unknown relation")
        for rel in (dimensions or {}):
            if rel not in self.vocabulary:
                bad.append(f"dimension map names an unknown relation {rel!r}")
        if bad:
            raise ValueError(
                "RelationAlgebra vocabulary/table mismatch: " + "; ".join(bad)
            )

        self._table: dict[Tuple[Hashable, Hashable], Composed] = dict(table)
        self._inverses: dict[Hashable, Hashable] = dict(inverses or {})
        self._dimensions: dict[Hashable, Dimension] = {
            r: Dimension(d) for r, d in (dimensions or {}).items()
        }

    # ── membership ────────────────────────────────────────────────
    def is_relation(self, name: Any) -> bool:
        """True if ``name`` is a relation in this algebra's vocabulary."""
        return name in self.vocabulary

    # ── composition ───────────────────────────────────────────────
    def compose(self, a: Hashable, b: Hashable) -> Composed:
        """Compose a two-step chain ``a`` then ``b``.

        Returns the resulting relation, :data:`ESCALATE` for a contested chain,
        or ``None`` when nothing follows (including any pair absent from the
        table)."""
        return self._table.get((a, b))

    def compose_path(self, chain: Iterable[Hashable]) -> Tuple[Composed, bool]:
        """Left-fold a path of relations into the relation it yields.

        Walks the chain start→end (the canonical order — composition is not
        assumed associative), returning ``(result, escalated)``:

        * an empty chain folds to ``(None, False)``;
        * a single relation folds to itself;
        * ``None`` at any step breaks the chain — nothing further can follow —
          and returns ``(None, escalated)`` with the escalation seen so far;
        * once a step is :data:`ESCALATE`, the result stays escalated but the
          fold continues optimistically from the next leg, so provenance of the
          remaining chain is preserved.
        """
        chain = list(chain)
        if not chain:
            return None, False
        acc: Composed = chain[0]
        escalated = False
        for nxt in chain[1:]:
            if isinstance(acc, _Escalate):
                escalated = True
                acc = nxt          # restart the fold from the next leg
                continue
            if acc is None or acc not in self.vocabulary:
                return None, escalated
            acc = self.compose(acc, nxt)
            if isinstance(acc, _Escalate):
                escalated = True
        if isinstance(acc, _Escalate):
            escalated = True
        return acc, escalated

    # ── inverse / dimension ───────────────────────────────────────
    def inverse(self, r: Hashable) -> Optional[Hashable]:
        """The dual relation where a clean one is declared, else ``None``."""
        return self._inverses.get(r)

    def dimension(self, r: Hashable) -> Dimension:
        """The 5D reasoning dimension a relation projects onto (default floor:
        ``RELATIONAL``), so a relation edge maps one-to-one into the graph."""
        return self._dimensions.get(r, self.default_dimension)
