# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Dedup — collapse records that say the same normative thing.

Ingest pipelines routinely deliver the *same* rule or norm more than once: the
identical Tatbestand→Rechtsfolge lifted from two sources, the same deontic act
stated by two authorities, one rule restated with its conditions in a different
order. Downstream reasoning (subsumption, conflict resolution, burden) should see
each distinct claim once, but provenance must survive — *who* said it must not be
lost in the merge.

This module derives a **canonical identity** for a record and groups records that
share it. Identity is what makes two claims the *same claim to reason about*:

  * a :class:`subsumption.Rule` is identified by its conditions (as a *frozenset*
    — order is irrelevant), its consequence, its act, and its modality. The
    ``exceptions`` (Ausnahme) are deliberately **excluded**: two rules with the
    same trigger and conclusion are the same rule even if one carries an extra
    carve-out — the exceptions are reconciled later, not treated as new identity.
  * a :class:`scenario.Norm` is identified by its act and its deontic modality.

Merging is order-stable and deterministic: the representative of a group is the
first record encountered with that identity, the records come out in first-
appearance order, and every merge records the *source ids* of its members in the
order they were seen — so the collapse is fully auditable and replayable.

This module CONSUMES the existing :class:`subsumption.Rule` and
:class:`scenario.Norm` — it does not redefine either. Pure stdlib. No governance,
no domain, no I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from .subsumption import Rule
from .scenario import Norm


@dataclass(frozen=True)
class CanonicalKey:
    """The identity a record is deduplicated on.

    ``conditions`` is a *frozenset* so condition order never affects identity;
    ``consequence``/``act``/``modality`` complete the Rule identity. For a Norm
    only ``act`` and ``modality`` (the deontic) carry meaning — ``conditions`` is
    empty and ``consequence`` is ``""``."""
    conditions: frozenset
    consequence: str
    act: str
    modality: str


@dataclass(frozen=True)
class MergeGroup:
    """One canonical identity and every record that collapsed onto it.

    ``representative`` is the first member encountered; ``sources`` are the member
    source ids in encounter order; ``members`` are the record objects themselves
    (first-appearance order)."""
    key: CanonicalKey
    representative: object
    sources: tuple
    members: tuple


@dataclass
class DedupResult:
    """Outcome of a :func:`dedup` pass.

    ``records`` are the representatives (one per distinct identity, first-
    appearance order); ``groups`` are the full :class:`MergeGroup`s; ``merge_map``
    maps each key to the tuple of member source ids that collapsed onto it."""
    records: list
    groups: list  # list[MergeGroup]
    merge_map: dict  # dict[CanonicalKey, tuple[str, ...]]


def canonical_key(record: "Rule | Norm") -> CanonicalKey:
    """Derive the :class:`CanonicalKey` of ``record``.

    A :class:`subsumption.Rule` maps to ``(frozenset(conditions), consequence,
    act, modality)`` — exceptions excluded. A :class:`scenario.Norm` maps to
    ``(frozenset(), "", act, deontic)``. Anything else raises ``TypeError`` (an
    unknown record has no canonical identity we can honestly assert)."""
    if isinstance(record, Rule):
        return CanonicalKey(
            conditions=frozenset(record.conditions),
            consequence=record.consequence,
            act=record.act,
            modality=record.modality,
        )
    if isinstance(record, Norm):
        return CanonicalKey(
            conditions=frozenset(),
            consequence="",
            act=record.act,
            modality=record.deontic,
        )
    raise TypeError(
        f"canonical_key: unsupported record type {type(record).__name__!r} "
        "(expected subsumption.Rule or scenario.Norm)"
    )


def _default_source_of(record: object) -> str:
    """Prefer an explicit ``.source``; fall back to ``.id``; else ``str(record)``.

    Empty/falsy attributes are skipped so a Rule with no source still yields its
    id rather than the empty string."""
    source = getattr(record, "source", None)
    if source:
        return str(source)
    ident = getattr(record, "id", None)
    if ident:
        return str(ident)
    return str(record)


def dedup(
    records: Iterable,
    *,
    source_of: Optional[Callable[[object], str]] = None,
) -> DedupResult:
    """Group ``records`` that share a :func:`canonical_key` into single entries.

    The pass is a single left-to-right sweep, so it is order-stable and
    deterministic: the first record seen for an identity is that group's
    representative, groups come out in first-appearance order, and each group's
    ``sources`` list the member source ids in the order encountered. ``source_of``
    resolves a record's source id (default: :func:`_default_source_of`, which
    prefers ``.source``, then ``.id``, then ``str(record)``).

    Returns a :class:`DedupResult` whose ``records`` are the representatives,
    ``groups`` the full :class:`MergeGroup`s, and ``merge_map`` maps each key to
    the tuple of member source ids."""
    resolve = source_of or _default_source_of

    order: list = []                 # keys in first-appearance order
    members: dict = {}               # key -> list[record]
    sources: dict = {}               # key -> list[str]

    for record in records:
        key = canonical_key(record)
        if key not in members:
            order.append(key)
            members[key] = []
            sources[key] = []
        members[key].append(record)
        sources[key].append(resolve(record))

    groups: list = []
    result_records: list = []
    merge_map: dict = {}
    for key in order:
        member_tuple = tuple(members[key])
        source_tuple = tuple(sources[key])
        representative = member_tuple[0]
        groups.append(
            MergeGroup(
                key=key,
                representative=representative,
                sources=source_tuple,
                members=member_tuple,
            )
        )
        result_records.append(representative)
        merge_map[key] = source_tuple

    return DedupResult(records=result_records, groups=groups, merge_map=merge_map)
