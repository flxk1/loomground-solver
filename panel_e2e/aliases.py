# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Declared act identities and non-identities — the L2 layer, human-reviewed.

Two tables, both visible and countable (nothing papered over):

``ALIASES`` — hand act → the ingested surface it DENOTES (same act, same
normative level; the surface is merely coarser). Size = extraction-coarseness
debt (Lane A shrinks it).

``NO_COUNTERPART`` — hand acts that BY DESIGN have no ingested counterpart,
with the reason. Found by the first corpus run: void-clause cases author their
deontic act at the REMEDY level (what the adjudicator does with the clause)
while ingestion extracts the SUBSTANTIVE-NORM level (what the statute
obliges) — different normative levels, so an alias would be dishonest. Size =
level-mismatch debt: closing it means either authoring substantive-level twin
acts in cases or teaching the ingester remedy-level norms (a Lane A/B design
choice, now a counted number).
"""

ALIASES: dict[str, dict[str, str]] = {
    # EMPTY since 2026-08-10 — and that is the point. The one entry this
    # table ever held (gdpr: "notify" -> the full ingested clause) was
    # retired by the Lane A levers landing together: the ingester records
    # the deadline surface span (loomground-ingest#6), the pack publishes
    # clause-level deadline cues, L1(a) trims span-exact, and the case
    # authors the substantive rider-retained act. alias_count == 0 is the
    # metric, not a vacancy.
}

NO_COUNTERPART: dict[str, dict[str, str]] = {
    "contract.employment.para622.notice_waiver": {
        "disregard_void_waiver": (
            "remedy-level act (adjudicator disregards the void waiver); the "
            "ingested norms are substantive-level (§622 notice obligations). "
            "Different normative levels — an alias would equate a remedy with "
            "a duty. Reviewed 2026-08-09."),
    },
    "statute.bgb.para309.clause_blacklist": {
        "disregard_void_clause": (
            "remedy-level act (what the adjudicator does with the void "
            "clause); the ingested nodes are VALIDITY-level constitutive "
            "norms (§309: the term is void — drafter's disability, "
            "counterparty's immunity). Different normative levels — an "
            "alias would equate a remedy with a validity effect. "
            "Reviewed 2026-08-10."),
    },
    "contract.music.para307.perpetual_buyout": {
        "disregard_void_clause": (
            "remedy-level act; the ingested nodes are VALIDITY-level "
            "constitutive norms (§307 void / §306 preserved+substitution). "
            "Same declared level-mismatch as bgb §309. Reviewed 2026-08-10."),
    },
}
