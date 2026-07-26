# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The injected ports and the api conveniences that ride on them.

NullGovernance is the no-op default; api.check must run a well-formed case to
PASS and a malformed one to VIOLATION, taking oversight from the injected
governance. The FakeNormSource in _fakes.py proves the NormSource port is
implementable by a host with a tiny in-memory corpus.
"""

from __future__ import annotations

from loomground_solver import (
    NullGovernance, NormSource, Governance, check,
)
from loomground_solver.contract import LEVELS

from _fakes import FakeNormSource


# ── NullGovernance behaves ────────────────────────────────────────────────────

def test_null_governance_is_autonomous_active_clean_and_silent():
    g = NullGovernance()
    assert g.oversight_level() == "autonomous"
    assert g.oversight_level() in LEVELS
    assert g.oversight_active() is True
    assert g.classify("anything at all") == {"findings": 0}
    assert g.record({"event": "x"}) is None


def test_null_governance_satisfies_the_governance_protocol():
    assert isinstance(NullGovernance(), Governance)


def test_default_service_satisfies_the_reasoning_service_protocol():
    # held_pinpoints is a corpus capability on NormSource, not part of the
    # transport-neutral service surface.
    from loomground_solver import ReasoningService
    from loomground_solver.service import default_service
    assert isinstance(default_service(), ReasoningService)


def test_fake_norm_source_satisfies_the_norm_source_protocol():
    src = FakeNormSource(spans=[{"entity": "gdpr", "pinpoint": "Art. 33(1)"}],
                         pinpoints={"Art. 33(1)"})
    assert isinstance(src, NormSource)
    assert src.norm_spans_for({"gdpr"}) == [{"entity": "gdpr", "pinpoint": "Art. 33(1)"}]
    assert src.norm_spans_for({"nope"}) == []
    assert src.held_pinpoints() == {"Art. 33(1)"}


# ── api.check runs a case, taking oversight from governance ───────────────────

def _wellformed() -> dict:
    return {
        "problem": {"text": "Do we notify?"},
        "grounds": [{"pinpoint": "Art. 33(1)", "receipted": True}],
        "facts": [{"text": "breach detected", "source": "SIEM alert 0815"}],
        "chain": [], "gaps": [], "actions": [],
        "resolution": {"type": "determinate", "answer": "72h"},
        "coverage": 1.0, "profile": "legal-de",
    }


def test_api_check_passes_a_wellformed_case_under_null_governance():
    rep = check(_wellformed())
    assert rep.ok
    assert not rep.must_escalate


def test_api_check_reports_violation_on_a_malformed_case():
    bad = _wellformed()
    bad["facts"] = [{"text": "customer requested erasure", "source": ""}]
    rep = check(bad)
    assert not rep.ok
    assert any(f.code == "RC-1" for f in rep.violations)


def test_api_check_escalates_when_governance_floor_is_breached():
    # an open, high-stake case under a low effective oversight level must not
    # pass — the judgment floor (R4) bites.
    open_case = _wellformed()
    open_case["resolution"] = {"type": "open", "note": ""}

    class ReviewGov:
        def oversight_level(self): return "review"
        def oversight_active(self): return True
        def classify(self, text): return {"findings": 0}
        def record(self, event): return None

    rep = check(open_case, governance=ReviewGov(), stake=True)
    assert not rep.ok
    assert any(f.code == "RC-4" for f in rep.violations)


def test_api_check_explicit_kw_overrides_governance_default():
    open_case = _wellformed()
    open_case["resolution"] = {"type": "open", "note": ""}
    # NullGovernance says autonomous, but an explicit approve level satisfies R4
    rep = check(open_case, oversight_level="approve", stake=True)
    assert not any(f.code == "RC-4" for f in rep.violations)
