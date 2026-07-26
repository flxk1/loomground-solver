# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Datapump — the verifier data-pump: verified runs → training data (rung 4).

Every governed run is a triple ``problem → candidate → verdict``, signed into
A host audit chain is a growing record of *checked* reasoning, and a
checked answer is exactly what supervised fine-tuning and preference training
want. This pure harvester turns the chain into the training set: it keeps the
runs that passed (optionally re-verifying each signature), de-duplicates, and
emits SFT examples plus preference pairs. A thin host adapter that maps chain
events onto :func:`harvest` records is host-side and out of scope here.

A **verified run** record::

    {"problem": str, "candidate": str, "passed": bool,
     "signature": str | None, "rationale": str, "trace": dict | None}

Pure stdlib. No governance, no domain."""
from __future__ import annotations

import json


def _key(record) -> tuple:
    return (record.get("problem", ""), record.get("candidate", ""))


def harvest(records, *, verify=None, dedup=True) -> dict:
    """Turn verified-run records into a training set.

    ``verify(record) -> bool`` (optional) drops records that fail (e.g. a replay
    signature re-check), counted as ``dropped_unverified``; a ``verify`` that
    *raises* on a record is treated as a drop, so one malformed record can't
    abort the whole harvest. ``dedup`` removes later records with a repeated
    ``(problem, candidate)`` key, counted as ``dropped_dupe``; a dropped
    duplicate whose ``passed`` flag disagrees with the kept record is also
    counted in ``conflicts`` (a data-integrity signal, not just a dupe).
    Returns ``{"examples", "preferences", "stats"}``:

      * ``examples`` — one ``{"prompt", "completion", "rationale"}`` per PASSED
        (and verified) record;
      * ``preferences`` — for each problem with at least one passed and one
        failed candidate, one ``{"prompt", "chosen", "rejected"}`` pair
        (deterministic ``sorted`` pick);
      * ``stats`` — the counts.
    """
    records = list(records)
    total = len(records)

    # 1. verification filter. A verify that raises on a malformed record must
    #    not abort harvesting the whole chain — treat a raise as a drop so one
    #    bad record loses only itself, not all the training data.
    if verify is not None:
        def _ok(r) -> bool:
            try:
                return bool(verify(r))
            except Exception:
                return False
        kept = [r for r in records if _ok(r)]
    else:
        kept = list(records)
    verified = len(kept)
    dropped_unverified = total - verified

    # 2. de-duplication by (problem, candidate).
    dropped_dupe = 0
    conflicts = 0
    if dedup:
        seen: dict = {}
        deduped = []
        for r in kept:
            k = _key(r)
            if k in seen:
                dropped_dupe += 1
                # Same (problem, candidate) with a disagreeing passed/failed
                # flag is a data-integrity conflict, not a plain duplicate —
                # surface it rather than silently keeping whichever arrived
                # first.
                if bool(r.get("passed")) != seen[k]:
                    conflicts += 1
                continue
            seen[k] = bool(r.get("passed"))
            deduped.append(r)
        kept = deduped

    # 3. SFT examples from passed records.
    examples = [
        {
            "prompt": r.get("problem", ""),
            "completion": r.get("candidate", ""),
            "rationale": r.get("rationale", ""),
        }
        for r in kept
        if r.get("passed")
    ]

    # 4. preference pairs: per problem, one (passed, failed) pair.
    by_problem: dict = {}
    for r in kept:
        by_problem.setdefault(r.get("problem", ""), {"passed": [], "failed": []})
        bucket = "passed" if r.get("passed") else "failed"
        by_problem[r.get("problem", "")][bucket].append(r.get("candidate", ""))

    preferences = []
    for problem in sorted(by_problem):
        groups = by_problem[problem]
        if groups["passed"] and groups["failed"]:
            preferences.append({
                "prompt": problem,
                "chosen": sorted(groups["passed"])[0],
                "rejected": sorted(groups["failed"])[0],
            })

    stats = {
        "total": total,
        "verified": verified,
        "kept_examples": len(examples),
        "preference_pairs": len(preferences),
        "dropped_unverified": dropped_unverified,
        "dropped_dupe": dropped_dupe,
        "conflicts": conflicts,
    }
    return {"examples": examples, "preferences": preferences, "stats": stats}


def to_jsonl(harvested) -> str:
    """Render the harvested ``examples`` as JSONL (one JSON object per line) for
    supervised fine-tuning — deterministic key order, one trailing-newline-free
    string."""
    lines = [
        json.dumps(ex, sort_keys=True, ensure_ascii=False)
        for ex in harvested.get("examples", [])
    ]
    return "\n".join(lines)
