# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Act canonicalization — the FROZEN cross-boundary identity contract.

Act identity is either MECHANICALLY EXACT or HUMAN-DECLARED, never inferred.

L1 ``canonical_act(text)``: purely mechanical — Unicode NFC, lowercase,
collapse whitespace, strip leading articles, strip trailing punctuation.
DELIBERATELY NO deadline-text removal (freeze refinement, 2026-08-09): the
ingester persists only the deadline's matched VALUE, not its surface span, so
span-exact removal is impossible from persisted data and substring re-search
would be a mini-inference that can over/under-remove. Until the ingester
records the span (a named Lane A item that will measurably shrink the alias
table), the deadline-clause difference rides in the alias — coarser, honest,
counted. Manner riders ("without undue delay") are MEANING — a standard of
conduct — and are likewise never stripped.

L2 ``acts_match(hand, ingested, aliases)``: if L1 forms differ, the ONLY path
to a match is an explicit, case-scoped alias (hand act → expected canonical
ingested surface), authored and reviewed with the case. No fuzzy fallback; a
mismatch without an alias fails loudly, naming both canonical forms.

THE METRIC (first-class, PO-locked): the alias-table size IS the
extraction-coarseness debt. The e2e scorecard reports alias_count per run —
Lane A's go/no-go is a number, not a vibe.
"""
from __future__ import annotations

import re
import unicodedata

_ARTICLES = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)
_WS = re.compile(r"\s+")


def canonical_act(text: str) -> str:
    """L1 canonical form — mechanical only, removes no content words."""
    s = unicodedata.normalize("NFC", str(text or ""))
    s = s.lower()
    s = _WS.sub(" ", s).strip()
    s = _ARTICLES.sub("", s)
    return s.strip(" ,.;:")


def acts_match(hand_act: str, ingested_act: str, *,
               aliases: dict[str, str] | None = None) -> tuple[bool, str, dict]:
    """L1-exact or L2-declared act identity.

    Returns (matched, level, detail): level ∈ {'L1','L2','none'}; detail
    always carries both canonical forms, and the alias used when L2 matched."""
    hand_c = canonical_act(hand_act)
    ing_c = canonical_act(ingested_act)
    detail: dict = {"hand_canonical": hand_c, "ingested_canonical": ing_c}
    if hand_c == ing_c:
        return True, "L1", detail
    alias = (aliases or {}).get(hand_act) or (aliases or {}).get(hand_c)
    if alias is not None:
        if canonical_act(alias) == ing_c:
            detail["alias_used"] = alias
            return True, "L2", detail
        detail["alias_mismatch"] = canonical_act(alias)
    return False, "none", detail
