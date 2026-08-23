# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""PROM-001 — host-observed `kind`, gate-computed `risk` (SPEC §4, §7.4; v0.11.0).

Loomground's TOKEN carries a single `kind` and a single `risk` field
(schema/token.schema.json); the specification amends what a CONFORMING
IMPLEMENTATION must do to arrive at those two values before a token reaches
``evaluate()``:

- **`kind` is host-observed, never actor-declared.** There is no actor-set
  `kind` (SPEC §4). This module's ``HostObservation.kind`` is what the host
  recorded at the tool-call/effect boundary; it is what lands on the governed
  token, unconditionally — an actor's claim is never consulted to set it.
- **`risk` is gate-computed** from a governed, versioned, signed POLICY TABLE
  keyed on (observed `kind` x target/resource x context x autonomy-grade). A
  self-declared hint is admitted only as a MONOTONIC RAISE-ONLY RATCHET: it may
  raise the computed tier, never lower it.
- **Unmapped resolves to the strictest tier by construction.**
- **Fail-closed floor:** an unclassifiable observation, or a declared-kind-vs-
  observed-kind mismatch, resolves to the strictest tier — never in the
  token's favour.
- **Dual log (§7.4):** the record carries BOTH the declared token and the
  host-observed facts, so a later redress weighs the claim against the
  observation rather than a reconciled summary.

The POLICY TABLE's content (which patterns map to which tier) is POLICY (SPEC
§10) — supplied by the caller, a deployer choice, never hardcoded here. This
module supplies the MECHANISM only: the risk ordering it ratchets over is read
from ``loomground_governance`` (the same source ``loomground.py`` reads RISKS
from), never re-declared.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from loomground_governance import vocabulary

# the SAME governance-sourced risk ordering `loomground.py` uses — read once
# here rather than imported cross-module, to keep this file a standalone peer
# (loomground.py may import prom001.py without a cycle).
RISKS = list(vocabulary("risk")["levels"])
RISK_RANK = {r: i for i, r in enumerate(RISKS)}
STRICTEST_RISK = RISKS[-1]           # the fail-closed floor tier (SPEC §4)
UNCLASSIFIABLE_KIND = "unclassifiable"  # sentinel: the host could not classify the operation


@dataclass(frozen=True)
class HostObservation:
    """What the host observed at the tool-call/effect boundary (SPEC §4).

    ``kind`` is ``None`` when the operation could not be classified at all —
    an unclassifiable token, one arm of the fail-closed floor. ``target``,
    ``context`` and ``grade`` are the remaining risk-table lookup keys
    (observed-kind x target/resource x context x autonomy-grade); ``grade`` is
    the proposing actor's autonomy grade at the point of observation.
    """
    kind: Optional[str]
    target: str = ""
    context: str = ""
    grade: Optional[str] = None


@dataclass(frozen=True)
class GovernedRiskTable:
    """A governed, versioned, signed policy table (SPEC §4).

    ``entries`` maps a ``(kind, target, context, grade)`` 4-tuple to a risk
    tier. An empty string in any position is this ENGINE's wildcard-matching
    convention (the table author's choice, not language or policy content
    added by this module): ``lookup()`` tries the exact key first, then
    progressively less specific keys with trailing positions wildcarded. If
    none matches, the pattern is genuinely unmapped and the caller floors to
    ``STRICTEST_RISK`` (SPEC §4: "a pattern the table does not map resolves to
    the strictest tier by construction"). Signature verification is outside
    this module's scope (key material, SPEC §10); ``signature`` is carried
    through to the dual log for audit only.
    """
    entries: Mapping[tuple[str, str, str, str], str] = field(default_factory=dict)
    version: str = "unversioned"
    signature: Optional[str] = None

    def lookup(self, kind: str, target: str = "", context: str = "", grade: str = "") -> Optional[str]:
        for key in (
            (kind, target, context, grade),
            (kind, target, context, ""),
            (kind, target, "", ""),
            (kind, "", "", ""),
        ):
            if key in self.entries:
                return self.entries[key]
        return None


@dataclass(frozen=True)
class GovernedEvaluation:
    """The PROM-001 dual-log record (SPEC §7.4): the declared token, the
    host-observed facts, and the governed outcome derived from them."""
    declared: Mapping[str, Any]
    observed: Mapping[str, Any]
    kind: str
    risk: str
    floored: bool
    floor_reason: Optional[str]
    token: dict[str, Any]  # the declared token with kind/risk replaced by the governed values


def govern_token(declared: Mapping[str, Any], observation: HostObservation,
                  table: GovernedRiskTable) -> GovernedEvaluation:
    """Compute the PROM-001 governed token from a declared token and a host
    observation (SPEC §4, §7.4).

    ``declared`` is the actor's proposed token (id/party/provenance/tags/
    reversibility/uncertainty pass through unchanged — only `kind` and `risk`
    are governed here). Returns a :class:`GovernedEvaluation` carrying the
    dual log and the governed token ready for ``evaluate()``.
    """
    declared_kind = declared.get("kind")
    floored = False
    floor_reason: Optional[str] = None

    if observation.kind is None:
        # the host could not classify the operation at all — unclassifiable is
        # never resolved from the actor's own claim (SPEC §4: "there is no
        # actor-set kind").
        kind = UNCLASSIFIABLE_KIND
        floored = True
        floor_reason = "unclassifiable: no host-observed kind"
    else:
        kind = observation.kind  # host-observed always governs; the actor's claim is never consulted
        if declared_kind is not None and declared_kind != observation.kind:
            floored = True
            floor_reason = (
                f"declared kind {declared_kind!r} != host-observed kind "
                f"{observation.kind!r} — host-observed governs, fail-closed floor"
            )

    if floored:
        risk = STRICTEST_RISK
    else:
        computed = table.lookup(kind, observation.target, observation.context, observation.grade or "")
        if computed is None:
            risk = STRICTEST_RISK
            floored = True
            floor_reason = (
                f"no risk-table entry for (kind={kind!r}, target={observation.target!r}, "
                f"context={observation.context!r}, grade={observation.grade!r}) — "
                f"unmapped resolves to the strictest tier"
            )
        else:
            risk = computed
            hint = declared.get("risk")
            # a self-declared hint is admitted ONLY as a monotonic raise-only
            # ratchet — it may raise the computed tier, never lower it.
            if hint in RISK_RANK and RISK_RANK[hint] > RISK_RANK[risk]:
                risk = hint

    token = dict(declared)
    token["kind"] = kind
    token["risk"] = risk

    return GovernedEvaluation(
        declared=dict(declared),
        observed={
            "kind": observation.kind,
            "target": observation.target,
            "context": observation.context,
            "grade": observation.grade,
            "table_version": table.version,
        },
        kind=kind, risk=risk, floored=floored, floor_reason=floor_reason, token=token,
    )
