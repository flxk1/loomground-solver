# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Act canonicalization — the FROZEN cross-boundary identity contract.

Act identity is either MECHANICALLY EXACT or HUMAN-DECLARED, never inferred.

L1 ``canonical_act(text)``: purely mechanical — Unicode NFC, lowercase,
collapse whitespace, strip leading articles, strip trailing punctuation.

L1(a) ``trim_recorded_deadline(action, surface)``: the anticipated amendment
(2026-08-10, after loomground-ingest#6 + the pack's clause-level deadline
cues) — the deadline clause is removed SPAN-EXACT using the surface the
ingester RECORDED at ingest time (``deadline_surface``: full published-cue
match, action-anchored offsets). The anchor is verified before cutting
(``action[start:end] == text``) and the function refuses loudly otherwise —
no re-search, no fuzzy cut, no removal when nothing was recorded. Manner
riders ("without undue delay") are MEANING — a standard of conduct — and are
never stripped.

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


def trim_recorded_deadline(action: str, surface: dict | None) -> str:
    """L1(a) — span-exact removal of the RECORDED deadline surface.

    Anchored and verified, never searched: the recorded surface must
    reproduce exactly at its recorded offsets or this refuses loudly.
    Returns the action unchanged when no surface was recorded."""
    if not surface:
        return action
    start, end, text = surface.get("start"), surface.get("end"), surface.get("text")
    if not (isinstance(start, int) and isinstance(end, int)
            and isinstance(text, str) and text):
        raise ValueError(f"malformed deadline_surface: {surface!r}")
    if action[start:end] != text:
        raise ValueError(
            "deadline_surface does not anchor: "
            f"action[{start}:{end}] == {action[start:end]!r} != {text!r}")
    return action[:start] + action[end:]


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
