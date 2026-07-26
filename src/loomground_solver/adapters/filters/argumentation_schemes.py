# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Fingerprint adapter for Walton-style argumentation schemes."""
from __future__ import annotations

from ...fingerprint import _get, register_filter


WALTON_CQ = {
    "cause-to-effect": 3,
    "practical-reasoning-consequences": 4,
    "analogy": 3,
    "expert-opinion-authority": 6,
    "established-rule": 3,
    "precedent": 3,
    "sign": 2,
    "temporal-succession": 2,
}

_DIM_TO_SCHEME = {
    "causal": "cause-to-effect",
    "intentional": "practical-reasoning-consequences",
    "relational": "analogy",
    "temporal": "temporal-succession",
}
_RULE_TO_SCHEME = {
    "lex-superior": "expert-opinion-authority",
    "lex-specialis": "established-rule",
    "lex-posterior": "temporal-succession",
}


def argumentation_schemes(context: dict) -> dict:
    """Count detected schemes and their open critical-question budget."""
    tags = {scheme: 0 for scheme in WALTON_CQ}
    for pair in context.get("pairs") or ():
        for edge in _get(pair, "edges", ()) or ():
            scheme = _DIM_TO_SCHEME.get(_get(edge, "dimension", None))
            if scheme:
                tags[scheme] += 1
    for rule in context.get("fired_rules") or ():
        scheme = _RULE_TO_SCHEME.get(rule)
        if scheme:
            tags[scheme] += 1
        if "precedent" in str(rule):
            tags["precedent"] += 1
    open_questions = sum(
        WALTON_CQ[scheme] for scheme, count in tags.items() if count > 0
    )
    return {**tags, "critical_questions_open": open_questions}


def register_argumentation_schemes() -> None:
    """Register the argumentation-schemes fingerprint adapter."""
    register_filter("argumentation_schemes", argumentation_schemes)
