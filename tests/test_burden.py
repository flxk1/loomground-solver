# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Burden of proof (O102-O105 + O107): allocation, standard of proof, rebuttable
presumptions, disproof-on-the-merits vs decided-by-burden, and *non-liquet*.

Imported straight from the module — the human supervisor wires the package
exports; these tests exercise the op in isolation."""
from __future__ import annotations

from loomground_solver.burden import (
    Standard,
    STANDARDS,
    meets,
    Element,
    Presumption,
    ElementFinding,
    BurdenReport,
    allocate,
)
from loomground_solver.cross_subsumption import Verdict


def test_proven_on_the_facts():
    rep = allocate([Element("h", "plaintiff")], {"h"})
    f = rep.finding_for("h")
    assert f.status == Verdict.SATISFIED
    assert f.established is True
    assert f.by_burden is False          # proven on the facts, not by the burden rule
    assert f.against == ""
    assert rep.all_established() is True


def test_non_liquet_decided_by_burden_not_guessed():
    rep = allocate([Element("h", "plaintiff")], set())
    f = rep.finding_for("h")
    assert f.status == Verdict.OPEN
    assert f.established is False         # the fact is never guessed (O107)
    assert f.by_burden is True
    assert f.against == "plaintiff"
    assert rep.all_established() is False


def test_standard_of_proof_scale_o104():
    e = Element("g", "state", standard=Standard.BEYOND_REASONABLE_DOUBT)

    # attained < required -> non-liquet, against the party bearing persuasion
    rep = allocate([e], {"g"}, proof={"g": Standard.PREPONDERANCE})
    f = rep.finding_for("g")
    assert f.status == Verdict.OPEN
    assert f.against == "state"
    assert f.established is False

    # attained == required -> proven
    rep2 = allocate([e], {"g"}, proof={"g": Standard.BEYOND_REASONABLE_DOUBT})
    assert rep2.finding_for("g").status == Verdict.SATISFIED
    assert rep2.finding_for("g").established is True

    # scale ordering and iteration order
    assert meets(Standard.GLAUBHAFT, Standard.PREPONDERANCE) is False
    assert meets(Standard.PREPONDERANCE, Standard.PREPONDERANCE) is True
    assert meets(Standard.BEYOND_REASONABLE_DOUBT, Standard.GLAUBHAFT) is True
    assert STANDARDS == (
        Standard.GLAUBHAFT,
        Standard.PREPONDERANCE,
        Standard.CLEAR_AND_CONVINCING,
        Standard.BEYOND_REASONABLE_DOUBT,
    )


def test_rebuttable_presumption_supplies_fact_o105():
    p = Presumption(supplies="paternity", basic_facts=("married",))
    rep = allocate([Element("paternity", "resp")], {"married"}, presumptions=[p])
    f = rep.finding_for("paternity")
    assert f.status == Verdict.SATISFIED
    assert f.presumed is True
    assert f.by_burden is False
    assert f.established is True


def test_presumption_rebutted_falls_away_to_non_liquet():
    p = Presumption(
        supplies="paternity",
        basic_facts=("married",),
        rebutted_by=("dna-excludes",),
    )
    rep = allocate(
        [Element("paternity", "resp")],
        {"married", "dna-excludes"},
        presumptions=[p],
    )
    f = rep.finding_for("paternity")
    assert f.status == Verdict.OPEN
    assert f.presumed is False
    assert f.against == "resp"
    assert f.established is False


def test_presumption_not_triggered_when_basic_facts_absent():
    p = Presumption(supplies="paternity", basic_facts=("married",))
    rep = allocate([Element("paternity", "resp")], set(), presumptions=[p])
    f = rep.finding_for("paternity")
    assert f.status == Verdict.OPEN
    assert f.presumed is False
    assert f.against == "resp"


def test_disproof_on_the_merits_vs_by_burden():
    # negation present -> disproven ON THE MERITS (a fact decided it)
    rep = allocate([Element("h", "pl")], {"-h"})
    f = rep.finding_for("h")
    assert f.status == Verdict.NOT_SATISFIED
    assert f.established is False
    assert f.by_burden is False          # decided against on the facts
    assert f.against == ""

    # contrast: mere absence -> decided against by the burden RULE
    rep2 = allocate([Element("h", "pl")], set())
    assert rep2.finding_for("h").status == Verdict.OPEN
    assert rep2.finding_for("h").by_burden is True


def test_multi_element_claim_and_serialisation():
    elements = [Element("duty", "pl"), Element("breach", "pl")]
    rep = allocate(elements, {"duty"})
    assert rep.finding_for("duty").status == Verdict.SATISFIED
    assert rep.finding_for("breach").status == Verdict.OPEN
    assert rep.all_established() is False

    d = rep.to_dict()
    assert isinstance(d["findings"], list) and len(d["findings"]) == 2
    duty_d, breach_d = d["findings"]
    for row in (duty_d, breach_d):
        assert {"status", "established", "by_burden", "against"} <= row.keys()
    assert duty_d["status"] == Verdict.SATISFIED
    assert breach_d["status"] == Verdict.OPEN
    assert breach_d["against"] == "pl"

    # input order is preserved
    assert [r["element"] for r in d["findings"]] == ["duty", "breach"]


def test_reports_and_findings_are_frozen():
    rep = allocate([Element("h", "pl")], {"h"})
    f = rep.finding_for("h")
    import pytest

    with pytest.raises((AttributeError, TypeError)):
        rep.findings = ()            # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        f.status = "x"               # type: ignore[misc]


def test_finding_for_missing_element_is_none():
    rep = allocate([Element("h", "pl")], {"h"})
    assert rep.finding_for("nope") is None


def test_production_burden_defaults_to_persuasion_party():
    # Element carries both burdens; production defaults to '' meaning "same party".
    e = Element("h", "plaintiff")
    assert e.production == ""
    assert e.persuasion == "plaintiff"
