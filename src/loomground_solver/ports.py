# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Injected ports — the seam between the universal solver and its hosts.

The solver package is imported unchanged by arbitrary host applications. It
carries no corpus and no governance of its own; those arrive through the thin
Protocol ports defined here. A host wires in a concrete ``NormSource`` (the
corpus it holds) and a concrete ``Governance`` (its oversight/lock/audit).
``NullGovernance`` is the no-op default so the solver runs standalone.

Pure stdlib (``typing`` only).
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class NormSource(Protocol):
    """What the case/reasoning layer needs to read norms/claims from a corpus.

    Modelled on what ``build_case`` reads from the rule registry: the per-article
    norm-spans the corpus holds for a set of instrument codes, and the set of
    pinpoints the corpus can actually verify (used by the R5 action check)."""

    def norm_spans_for(self, instrument_codes: set) -> list[dict]:
        """The norm-span dicts held for the given instrument codes."""
        ...

    def held_pinpoints(self) -> set:
        """The set of pinpoints the corpus actually holds (for R5 verification)."""
        ...


@runtime_checkable
class EvidenceProvider(Protocol):
    """Resolve and verify stable evidence references from any knowledge store."""

    def resolve(self, ref: "EvidenceRef") -> dict:
        """Return the evidence payload identified by ``ref``."""
        ...

    def verify(self, ref: "EvidenceRef") -> bool:
        """Confirm source, digest, item and span consistency for ``ref``."""
        ...


@runtime_checkable
class CandidateProvider(Protocol):
    """Produce untrusted candidates; ranking is never proof or truth weight."""

    def candidates(self, problem: dict, *, limit: int = 10) -> list["Candidate"]:
        ...


@runtime_checkable
class StructuralCompiler(Protocol):
    """Compile a producer's advertised structural schema into Solver-neutral data."""

    def supports(self, schema: str) -> bool:
        ...

    def compile(self, candidate: "Candidate") -> dict:
        """Return ``{pairs, attacks}`` for one candidate."""
        ...


@runtime_checkable
class ReasoningService(Protocol):
    """Transport-neutral surface exposed by any conforming solver."""

    def manifest(self) -> dict:
        """Return a ``reasoning.interop`` protocol manifest."""
        ...

    def verify(self, request: dict) -> dict:
        """Accept a reasoning-request dictionary and return a result dictionary."""
        ...


#: A model call: prompt text in, completion text out. Injected by the host so
#: the package never binds a particular model runtime.
ModelFn = Callable[[str], str]


@runtime_checkable
class Governance(Protocol):
    """The oversight/lock/audit surface a host injects.

    Covers R4 (policy oversight level + active flag), R6 (lock-classify at the
    export boundary), and the audit sink (record)."""

    def oversight_level(self) -> str:
        """The configured default oversight level (one of contract.LEVELS)."""
        ...

    def oversight_active(self) -> bool:
        """Whether oversight is switched on (False drops effective level to autonomous)."""
        ...

    def classify(self, text: str) -> dict:
        """Lock/privacy classification of a text; returns e.g. {'findings': int}."""
        ...

    def record(self, event: dict) -> None:
        """Append an event to the audit sink. May be a no-op."""
        ...


class NullGovernance:
    """Concrete no-op governance: autonomous, active, no findings, writes nothing.

    The standalone default when no host governance is injected."""

    def oversight_level(self) -> str:
        return "autonomous"

    def oversight_active(self) -> bool:
        return True

    def classify(self, text: str) -> dict:
        return {"findings": 0}

    def record(self, event: dict) -> None:
        return None


@runtime_checkable
class Signer(Protocol):
    """Signs a scenario-derivation trace for tamper-evident replay (rung 4).

    The default is a content hash (:class:`replay.HashSigner`); a host that has a
    real host key injects that instead. The package never binds
    a key or a crypto backend."""

    def sign(self, payload: bytes) -> str:
        """Return a signature/digest string over ``payload``."""
        ...

    def verify(self, payload: bytes, signature: str) -> bool:
        """True iff ``signature`` matches ``payload``."""
        ...
