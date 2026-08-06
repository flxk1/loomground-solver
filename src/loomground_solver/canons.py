# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Canon-set selection (O147) — the ordered interpretive canons a legal family
uses, and a selector from family to canon set.

Every legal tradition carries a *canon of construction*: an ordered repertoire
of interpretive moves, with a rule for what breaks ties (and, sometimes, an
outer limit no reading may cross). This module is a **registry + selector**. It
returns the ordered canon set and its tie-breaker for a family; it does **not
interpret** — turning a canon into a reading of a concrete text is the unbuilt
Family E, and is deliberately out of scope here. Selecting the canon set is
data; applying it is judgment.

Four families ship:

  * ``CIVIL_LAW`` — Savigny's quartet (grammatical, systematic, historical,
    teleological). Teleology breaks ties; the grammatical (wording) meaning is
    the outer cap a reading may not cross.
  * ``COMMON_LAW`` — canons of construction (ordinary-meaning, noscitur a
    sociis, ejusdem generis, expressio unius) plus purpose; purpose breaks ties.
  * ``USUL_AL_FIQH`` — the classical Sunni source order (Qurʾān, Sunna, ijmāʿ,
    qiyās); the highest source, the Qurʾān, governs a tie.
  * ``US_TEXTUALIST`` — text, structure, original public meaning; text breaks
    ties.

The registry keys on a canonical family id and a small set of pure synonyms
(``savigny`` → civil-law, ``islamic`` → usul-al-fiqh, …). It does **not** guess
a family from a jurisdiction code: a jurisdiction may host more than one
tradition (US courts use both construction canons and textualism), and picking
between them is an interpretive act this selector does not perform.

Deterministic, pure stdlib.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonSet:
    """An ordered interpretive canon set for a legal family.

    ``canons`` is an ordered tuple (highest-priority / first-applied first).
    ``tiebreaker`` names the canon that governs when the ordered application
    leaves a genuine tie — it is always a member of ``canons``. ``cap``, when
    non-empty, names the canon that is an outer limit no reading may cross
    (e.g. the wording cap in the civil-law tradition); it too is a member of
    ``canons``. ``cap`` is empty where the tradition recognises no such hard
    outer limit — recorded honestly rather than invented."""
    family: str
    canons: tuple[str, ...]
    tiebreaker: str
    cap: str = ""
    label: str = ""


# ── the four canon sets ──────────────────────────────────────────────────────

CIVIL_LAW = CanonSet(
    family="civil-law",
    canons=("grammatical", "systematic", "historical", "teleological"),
    tiebreaker="teleological",   # objective purpose breaks the tie
    cap="grammatical",           # wording is the outer limit (Wortlautgrenze)
    label="Savigny quartet (grammatical / systematic / historical / teleological)",
)

COMMON_LAW = CanonSet(
    family="common-law",
    canons=("ordinary-meaning", "noscitur-a-sociis", "ejusdem-generis",
            "expressio-unius", "purpose"),
    tiebreaker="purpose",        # legislative purpose resolves a residual tie
    cap="",                      # no single hard outer cap across the tradition
    label="Common-law canons of construction (+ purpose)",
)

USUL_AL_FIQH = CanonSet(
    family="usul-al-fiqh",
    canons=("quran", "sunna", "ijma", "qiyas"),
    tiebreaker="quran",          # the highest source governs
    cap="",
    label="Uṣūl al-fiqh source order (Qurʾān / Sunna / ijmāʿ / qiyās)",
)

US_TEXTUALIST = CanonSet(
    family="us-textualist",
    canons=("text", "structure", "original-public-meaning"),
    tiebreaker="text",           # the textualist anchor
    cap="",
    label="US textualist / originalist (text / structure / original public meaning)",
)


# ── registry + selector ──────────────────────────────────────────────────────

#: Canon sets keyed by canonical family id.
CANON_SETS: dict[str, CanonSet] = {
    cs.family: cs for cs in (CIVIL_LAW, COMMON_LAW, USUL_AL_FIQH, US_TEXTUALIST)
}

#: The canonical family ids.
FAMILIES: tuple[str, ...] = tuple(CANON_SETS)

#: Pure family synonyms → canonical family id. These are alternative NAMES for
#: the same tradition, never jurisdiction guesses (a jurisdiction may host more
#: than one family, and choosing between them is interpretation, not selection).
_ALIASES: dict[str, str] = {
    "civil-law": "civil-law",
    "civil": "civil-law",
    "continental": "civil-law",
    "savigny": "civil-law",
    "common-law": "common-law",
    "common": "common-law",
    "construction": "common-law",
    "usul-al-fiqh": "usul-al-fiqh",
    "usul": "usul-al-fiqh",
    "islamic": "usul-al-fiqh",
    "us-textualist": "us-textualist",
    "textualist": "us-textualist",
    "originalist": "us-textualist",
}


def canon_set_for(family: str) -> CanonSet:
    """Return the ordered :class:`CanonSet` for a legal family (canonical id or a
    registered synonym). Raises :class:`KeyError` on an unknown family — an
    unrecognised family is never mapped to a default canon set. This SELECTS the
    canon set; it does not interpret any text with it."""
    key = (family or "").strip().lower()
    canonical = _ALIASES.get(key)
    if canonical is None:
        raise KeyError(
            f"unknown legal family: {family!r} (known: {FAMILIES})"
        )
    return CANON_SETS[canonical]


def tiebreaker_for(family: str) -> str:
    """Convenience: the tie-breaking canon for a family. Raises :class:`KeyError`
    on an unknown family."""
    return canon_set_for(family).tiebreaker
