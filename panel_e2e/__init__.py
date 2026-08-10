# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""panel_e2e — the graded panel's END-TO-END lane over the real planes.

The in-process panel (src/loomground_solver/eval/panel) proves the engine;
this package proves the PIPELINE: statute text → loomground-ingest
(DeonticIngester) → Versum store → reload → reconstructed solver Scenario →
derive → captured trace → replay-from-versum. Deliberately OUTSIDE
src/loomground_solver/ so the solver's purity invariant
(tests/test_dependency_inversion.py) stays untouched: the solver imports no
other plane; this package imports all of them.

Honest scope (load-bearing): only what DeonticIngester actually lowers goes
end-to-end. Results carry a LEVEL: ``derivation`` (conduct norms — full
reconstruct → derive → capture → replay-from-versum) or ``validity``
(constitutive validity nodes — void/preserved/substitution persisted and
reconstructed; nothing to derive, and the result says so). Stages the
ingester does not lower yet (intentional / structural / quantitative
constructions) run in-process and are MARKED in_process_fallback in every
result — an honest gap and a backlog item, never faked as reconstructed.

Running (not collected by CI: pytest testpaths = ["tests"], and the sibling
planes are not solver dependencies — the purity invariant, again): install
loomground-ingest, loomground-versum and loomground-deontic (>=0.1.3)
alongside the solver, then

    python -m panel_e2e.corpus      # the scorecard: verdict + debt columns
    python -m panel_e2e.harness <case-module>   # one case, tri-state
    python -m panel_e2e.spike_roundtrip         # Phase-0 minimal round-trip

Exit 0 = PASS or UNLOWERED (a named coverage gap); FAIL means breakage.
"""
