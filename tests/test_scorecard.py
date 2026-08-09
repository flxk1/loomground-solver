# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""S5 — the DoD scorecard must show the panel HITS HIGH: every case reaches its
correct terminal, every step is sourced+warranted, fabrication rate is 0 under
adversarial probes, and every run is contract-graded. Policy (H5) is graded only
when policy cases are present. This is the DoD's completion signal (§4.5)."""
from __future__ import annotations

from loomground_solver.eval.panel.scorecard import dod_scorecard


def test_panel_hits_high():
    sc = dod_scorecard()
    assert sc.n_cases >= 10, "panel corpus should be populated"
    # H1-H4 must be clean across the whole corpus
    for h in ("H1", "H2", "H3", "H4"):
        assert sc.bars[h].clean, f"{h} not clean: {sc.bars[h].failures}"
    # the load-bearing honesty invariant
    assert sc.fabrication_rate == 0.0, "fabrication under adversarial probes must be 0"
    # H5 clean iff there are policy cases (else vacuously pending)
    assert sc.bars["H5"].clean
    assert sc.hit_high is True


def test_scorecard_renders():
    text = dod_scorecard().render()
    assert "HIT HIGH: YES" in text
    assert "fabrication rate under adversarial probes: 0%" in text


def test_terminal_coverage_is_broad():
    # a real panel exercises every terminal state, not just DETERMINATE
    dist = dod_scorecard().terminal_distribution
    for term in ("determinate", "not_met", "escalate", "residual"):
        assert dist.get(term, 0) >= 1, f"panel lacks a {term} case"
