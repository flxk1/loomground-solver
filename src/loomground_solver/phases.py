# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Phase briefs for the reasoning walker — the pattern, taught in model-sized bites.

The whitepaper (docs/WHITEPAPER_reasoning-pattern.md) states the universal
pattern: Question → Facts → Norms → Application → Resolution → Action, as a
defeasible Toulmin loop. A local model that is handed ONE phase must get a
short, imperative explanation of that phase — what it receives, what rule it
must satisfy (the contract invariant), what it must output, and when it must
refuse. This module holds those briefs as data.

Design constraints (so a 3B-class local model can follow them):
  * each brief stays under ~900 characters;
  * output is strict JSON with named keys — nothing free-form;
  * each brief names its contract invariant and the refusal rule;
  * profile vocabularies are injected, never hard-coded in prose.

`curriculum()` returns the whole pattern as one teaching page (the compressed
whitepaper) for system prompts or skill bodies. Pure stdlib.

Internal by design: curriculum briefs consumed by the reasoning walker, not an operator surface.
"""

from __future__ import annotations

from .contract import DEFAULT_PROFILE, PROFILES

# ── the six phases ────────────────────────────────────────────────────────────

PHASE_ORDER = ("question", "facts", "norms", "application", "resolution", "action")

_BRIEFS: dict[str, str] = {
    "question": (
        "PHASE 1 of 6 — QUESTION. You receive a raw task or clause. Restate it "
        "as ONE answerable question. Do not answer it. Do not add facts. "
        "Output JSON: {\"question\": str}. Refuse (output {\"refuse\": reason}) "
        "if the task contains several unrelated questions — they must be split, "
        "one case each."
    ),
    "facts": (
        "PHASE 2 of 6 — FACTS. You receive the question and the available "
        "context. List the factual premises the answer will rest on. RULE R1: "
        "every fact MUST carry a source (document, exhibit, statement). A fact "
        "you cannot source does not go in the list — put it in 'unsourced' "
        "instead so a human sees what is missing. Never invent facts. "
        "Output JSON: {\"facts\": [{\"text\": str, \"source\": str}], "
        "\"unsourced\": [str]}."
    ),
    "norms": (
        "PHASE 3 of 6 — NORMS. You receive the question, the facts, and a list "
        "of norm-spans retrieved from the corpus (pinpoint + text). Select the "
        "provisions that govern the question; name any provision you know is "
        "needed but is NOT in the list — that is a gap and must be reported, "
        "never papered over. RULE R1: you may only select from the given list; "
        "you may not quote law from memory. "
        "Output JSON: {\"selected\": [pinpoint], \"gaps\": [pinpoint], "
        "\"why\": str}."
    ),
    "application": (
        "PHASE 4 of 6 — APPLICATION. You receive the question and the selected "
        "norms. Build the ABSTRACT reasoning schema — the frame any case of "
        "this kind must walk, NOT this case's outcome. Use EXACTLY the step "
        "names given in STEPS. Each step states its test as a QUESTION or "
        "criteria list: what must be examined, never whether it is met. Do NOT "
        "use the facts; do NOT subsume; do NOT conclude. The final step states "
        "the conditional fork (if criteria met and no exception: X; if "
        "exception engaged: Y), both branches open. RULE R2: every step needs "
        "a 'warrant' — what licenses it — and the warrant names its METHOD: "
        "verbatim (the wording), systematic (surrounding paragraphs, "
        "cross-references, the act's structure), historic (legislative "
        "history), or telos (the provision's purpose). RULE R8: read the norm "
        "to the END — every 'unless', every further paragraph (notification "
        "content lists, form requirements), every cross-referenced article "
        "gets its own step; a half-read norm is a wrong norm. If you cannot "
        "warrant a step, set \"unwarranted\": true. "
        "Output JSON: {\"chain\": [{\"step\": str, \"text\": str, "
        "\"warrant\": str, \"canon\": \"verbatim\"|\"systematic\"|"
        "\"historic\"|\"telos\"}]}."
    ),
    "resolution": (
        "PHASE 5 of 6 — RESOLUTION. You receive the abstract schema and the "
        "facts. You are a reasoning machine, not a judge: you NEVER decide. "
        "Lay out the supported READINGS — each a way the schema can close on "
        "these facts, with its grounds (pinpoints) and its consequences. One "
        "compelled reading: output it as the single reading; a human must "
        "still ratify it. Several supported readings (discretion, conflicting "
        "norms, open priority): output them all; a human chooses. Schema does "
        "not close: output zero readings and say why. RULE R4: no reading is "
        "marked preferred, recommended or default. "
        "Output JSON: {\"readings\": [{\"id\": str, \"label\": str, "
        "\"grounds\": [str], \"consequences\": [str]}], \"esc_reason\": str, "
        "\"why_open\": str}."
    ),
    "action": (
        "PHASE 6 of 6 — ACTION. You receive a resolved case (a determinate "
        "answer, or a residual with a recorded human choice). Extract what must "
        "now be done. RULE R5: every action cites the norm it derives from "
        "(source_norm); an action you cannot anchor is dropped, not guessed. "
        "If the case is OPEN you output an empty list — nothing may be done on "
        "an open question. "
        "Output JSON: {\"actions\": [{\"obligation\": str, \"actor\": str, "
        "\"deadline\": str, \"source_norm\": str}]}."
    ),
}


def brief(phase: str, *, profile: str = DEFAULT_PROFILE) -> str:
    """The phase brief a model receives, with the profile's step vocabulary
    injected where the phase needs it."""
    if phase not in _BRIEFS:
        raise ValueError(f"unknown phase {phase!r} (known: {PHASE_ORDER})")
    text = _BRIEFS[phase]
    prof = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])
    if phase == "application":
        steps = " -> ".join(s.capitalize() for s in prof["steps"])
        text += f" STEPS ({prof['label']}): {steps}."
    return text


def curriculum(*, profile: str = DEFAULT_PROFILE) -> str:
    """The whole pattern on one teaching page — the compressed whitepaper, for
    a system prompt or a skill body. Under 2500 characters by design."""
    prof = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])
    steps = " -> ".join(s.capitalize() for s in prof["steps"])
    return (
        "THE REASONING PATTERN (one defeasible loop; see "
        "docs/WHITEPAPER_reasoning-pattern.md).\n"
        "IRAC, Gutachtenstil and Fact-Rule-Meaning-Action are write-up formats. "
        "Underneath all of them sits one loop, run per question:\n\n"
        "  QUESTION  -> one answerable question, nothing else.\n"
        "  FACTS     -> premises, each with a source. Unsourced = reported, "
        "never used (R1).\n"
        "  NORMS     -> provisions selected from the retrieved corpus only; "
        "what is missing is a GAP, stated openly (R1).\n"
        "  APPLY     -> the ABSTRACT schema, step by step (" + steps + "): "
        "each step states its test as a question, with its warrant - the "
        "words that license the move (R2) - and the warrant names its canon: "
        "verbatim, systematic, historic, or telos (the four methods of "
        "interpretation). Read the norm to the END: its exceptions "
        "('unless...'), its further paragraphs (content and form "
        "requirements), its cross-references - each is a step, never a "
        "footnote (R8). The schema is case-free: it never subsumes, never "
        "concludes.\n"
        "  RESOLVE   -> the machine is a reasoning machine, never a judge: it "
        "lays out the supported READINGS with grounds and consequences, none "
        "marked preferred. One compelled reading - a human RATIFIES it. "
        "Several - a human CHOOSES, with a rationale (R3/R4). None - OPEN, "
        "said openly.\n"
        "  ACT       -> obligations that follow, each citing its source norm "
        "(R5). Nothing is done on an open question.\n\n"
        "Honesty rules that override everything: never invent a fact, a "
        "provision, a warrant or a date; gaps and unwarranted steps are "
        "surfaced, not smoothed; a one-option choice is a disguised answer; "
        "confidence is shown as coverage (receipts over required rooms), "
        "never as tone. The output of the loop is a case record; the "
        "reasoning contract checks it mechanically before it stands."
    )


def all_briefs(*, profile: str = DEFAULT_PROFILE) -> dict[str, str]:
    return {p: brief(p, profile=profile) for p in PHASE_ORDER}
