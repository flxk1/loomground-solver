# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Tiny in-memory fakes implementing the injected ports.

The package carries no corpus; a host injects one through
:class:`loomground_solver.ports.NormSource`. Ported tests that would otherwise
need a real ``rule_registry`` build a ``FakeNormSource`` here instead — a
minimal dict-backed corpus, faithful to what ``build_case`` reads from a
registry (``norm_spans_for`` + ``held_pinpoints``).
"""

from __future__ import annotations


class FakeNormSource:
    """A dict-backed NormSource: a corpus of norm-span dicts keyed nowhere in
    particular, plus the set of pinpoints it can verify."""

    def __init__(self, spans=None, pinpoints=None):
        self._spans = list(spans or [])
        self._pinpoints = set(pinpoints or [])

    def norm_spans_for(self, instrument_codes: set) -> list[dict]:
        codes = set(instrument_codes or ())
        if not codes:
            return list(self._spans)
        return [s for s in self._spans if s.get("entity") in codes
                or s.get("instrument") in codes]

    def held_pinpoints(self) -> set:
        return set(self._pinpoints)
