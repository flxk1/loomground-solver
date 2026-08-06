# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""O147 — canon-set selection: an ordered interpretive canon set per legal
family, each with a tie-breaker (and, where a tradition has one, a wording cap).
The selector RETURNS the canon set; it does not interpret any text — that is the
unbuilt Family E, deliberately out of scope."""
from __future__ import annotations

from loomground_solver.canons import (
    CIVIL_LAW, COMMON_LAW, USUL_AL_FIQH, US_TEXTUALIST,
    CANON_SETS, FAMILIES, canon_set_for, tiebreaker_for,
)


# ── the four families return their ordered canon set + tie-breaker ───────────

def test_civil_law_savigny_quartet_teleology_breaks_ties_wording_caps():
    cs = canon_set_for("civil-law")
    assert cs is CIVIL_LAW
    assert cs.canons == ("grammatical", "systematic", "historical", "teleological")
    assert cs.tiebreaker == "teleological"
    assert cs.cap == "grammatical"          # the Wortlautgrenze


def test_common_law_construction_canons_purpose_breaks_ties():
    cs = canon_set_for("common-law")
    assert cs.canons == ("ordinary-meaning", "noscitur-a-sociis",
                         "ejusdem-generis", "expressio-unius", "purpose")
    assert cs.tiebreaker == "purpose"
    # ejusdem generis follows noscitur a sociis in the ordering
    assert cs.canons.index("ejusdem-generis") > cs.canons.index("noscitur-a-sociis")


def test_usul_al_fiqh_source_order_quran_governs():
    cs = canon_set_for("usul-al-fiqh")
    assert cs.canons == ("quran", "sunna", "ijma", "qiyas")
    assert cs.tiebreaker == "quran"


def test_us_textualist_order_text_breaks_ties():
    cs = canon_set_for("us-textualist")
    assert cs.canons == ("text", "structure", "original-public-meaning")
    assert cs.tiebreaker == "text"


# ── selector accepts pure family synonyms (not jurisdiction guesses) ─────────

def test_family_synonyms_resolve_and_are_case_insensitive():
    assert canon_set_for("savigny") is CIVIL_LAW
    assert canon_set_for("Islamic") is USUL_AL_FIQH
    assert canon_set_for("originalist") is US_TEXTUALIST
    assert tiebreaker_for("continental") == "teleological"


# ── structural honesty invariants + unknown-family discipline ────────────────

def test_tiebreaker_and_cap_are_always_members_of_the_canon_set():
    # the selector returns DATA: a tie-breaker (and any cap) must be one of the
    # canons it ships — it never names a move outside the set it selected.
    for fam in FAMILIES:
        cs = CANON_SETS[fam]
        assert cs.tiebreaker in cs.canons
        assert cs.cap == "" or cs.cap in cs.canons


def test_unknown_family_raises_never_defaults():
    for bad in ("", "martian-law", "roman"):
        try:
            canon_set_for(bad)
        except KeyError:
            continue
        raise AssertionError(f"expected KeyError for family {bad!r}")
