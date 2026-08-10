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
    "statute.gdpr.art33.breach_notification": {
        # Same obligation, same level: the hand token names the act whose full
        # surface (incl. the manner rider + embedded deadline text the ingester
        # keeps today) is the ingested clause. Reviewed 2026-08-09.
        "notify": ("notify the supervisory authority without undue delay and, "
                   "where feasible, not later than 72 hours after having "
                   "become aware of it,"),
    },
}

NO_COUNTERPART: dict[str, dict[str, str]] = {
    "contract.employment.para622.notice_waiver": {
        "disregard_void_waiver": (
            "remedy-level act (adjudicator disregards the void waiver); the "
            "ingested norms are substantive-level (§622 notice obligations). "
            "Different normative levels — an alias would equate a remedy with "
            "a duty. Reviewed 2026-08-09."),
    },
}
