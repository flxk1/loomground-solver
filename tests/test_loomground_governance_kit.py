# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Standing gate: the Loomground evaluator (src/loomground_solver/loomground.py)
MUST pass every vector the language repository's governance package publishes.

This is the solver side of the clean-room contract: the language's own
neutral conformance kit (`loomground_governance.run_conformance`) drives this
module's parse/validate/project/validate_token/evaluate/evaluate_log exactly
as any other conforming implementation, with no solver-specific branching. A
future change to loomground.py that regresses a vector — a missing reason
code, a weakened guard, a determinism break — fails HERE, not only in a
release-gate CI job days later.

Skipped (not failed) only when the governance package is not importable at
all — e.g. a trimmed dev install without the sibling package — which is
itself reported as the skip reason, not silently swallowed.
"""
from __future__ import annotations

import pytest

from loomground_solver import loomground

try:
    from loomground_governance import run_conformance
except ImportError as exc:  # pragma: no cover - exercised only on a trimmed install
    run_conformance = None
    _import_error = exc
else:
    _import_error = None


@pytest.mark.skipif(
    run_conformance is None,
    reason=f"loomground_governance is not installed: {_import_error}",
)
def test_evaluator_passes_every_published_vector():
    report = run_conformance(loomground)
    failures = [f"{f['name']} ({f['kind']}): {f['error']}" for f in report.failures]
    assert report.ok, (
        f"{report.passed}/{report.total} governance-kit vectors passed; "
        f"failures:\n  " + "\n  ".join(failures)
    )
    assert report.total > 0, "the governance package published no vectors to check"
