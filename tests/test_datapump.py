# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The verifier data-pump: signed, verified runs become SFT examples and
preference pairs."""
from __future__ import annotations

import json

from loomground_solver import harvest, to_jsonl


def _rec(problem, candidate, passed, **kw):
    base = {"problem": problem, "candidate": candidate, "passed": passed,
            "signature": None, "rationale": "because", "trace": None}
    base.update(kw)
    return base


# ── examples ─────────────────────────────────────────────────────────────────

def test_passed_records_become_examples():
    records = [
        _rec("P1", "answer-a", True, rationale="entailed"),
        _rec("P2", "answer-b", False),
    ]
    out = harvest(records)
    assert len(out["examples"]) == 1
    ex = out["examples"][0]
    assert ex == {"prompt": "P1", "completion": "answer-a", "rationale": "entailed"}
    assert out["stats"]["kept_examples"] == 1
    assert out["stats"]["total"] == 2


# ── preferences ──────────────────────────────────────────────────────────────

def test_problem_with_pass_and_fail_yields_one_preference_pair():
    records = [
        _rec("P1", "good", True),
        _rec("P1", "bad", False),
        _rec("P2", "solo", True),          # no failed sibling -> no pair
    ]
    out = harvest(records)
    assert len(out["preferences"]) == 1
    pref = out["preferences"][0]
    assert pref == {"prompt": "P1", "chosen": "good", "rejected": "bad"}
    assert out["stats"]["preference_pairs"] == 1


def test_preference_pick_is_deterministic_sorted():
    records = [
        _rec("P1", "zeta", True),
        _rec("P1", "alpha", True),
        _rec("P1", "yankee", False),
        _rec("P1", "bravo", False),
    ]
    out = harvest(records)
    pref = out["preferences"][0]
    assert pref["chosen"] == "alpha"
    assert pref["rejected"] == "bravo"


# ── verify filter ────────────────────────────────────────────────────────────

def test_verify_drops_unverified_and_counts():
    records = [
        _rec("P1", "a", True, signature="ok"),
        _rec("P2", "b", True, signature="bad"),
    ]
    out = harvest(records, verify=lambda r: r["signature"] == "ok")
    assert out["stats"]["dropped_unverified"] == 1
    assert out["stats"]["verified"] == 1
    assert len(out["examples"]) == 1
    assert out["examples"][0]["prompt"] == "P1"


# ── dedup ────────────────────────────────────────────────────────────────────

def test_dedup_drops_duplicates():
    records = [
        _rec("P1", "a", True),
        _rec("P1", "a", True),          # exact (problem, candidate) dupe
        _rec("P1", "b", True),
    ]
    out = harvest(records, dedup=True)
    assert out["stats"]["dropped_dupe"] == 1
    assert len(out["examples"]) == 2


def test_dedup_off_keeps_duplicates():
    records = [_rec("P1", "a", True), _rec("P1", "a", True)]
    out = harvest(records, dedup=False)
    assert out["stats"]["dropped_dupe"] == 0
    assert len(out["examples"]) == 2


def test_conflicting_passed_flag_on_same_candidate_is_surfaced():
    # same (problem, candidate) but disagreeing pass/fail — a data-integrity
    # conflict that must not be silently collapsed to a plain dupe.
    records = [
        _rec("P1", "a", True),
        _rec("P1", "a", False),
    ]
    out = harvest(records, dedup=True)
    assert out["stats"]["conflicts"] == 1
    assert out["stats"]["dropped_dupe"] == 1


def test_plain_duplicate_is_not_counted_as_conflict():
    records = [_rec("P1", "a", True), _rec("P1", "a", True)]
    out = harvest(records, dedup=True)
    assert out["stats"]["dropped_dupe"] == 1
    assert out["stats"]["conflicts"] == 0


# ── resilience: a raising verify must not abort the whole harvest ─────────────

def test_raising_verify_drops_only_the_bad_record():
    def verify(r):
        if r["signature"] == "malformed":
            raise ValueError("bad signature")
        return r["signature"] == "ok"

    records = [
        _rec("P1", "a", True, signature="ok"),
        _rec("P2", "b", True, signature="malformed"),
        _rec("P3", "c", True, signature="ok"),
    ]
    out = harvest(records, verify=verify)
    # the raising record is dropped, the rest survive.
    assert out["stats"]["verified"] == 2
    assert out["stats"]["dropped_unverified"] == 1
    prompts = {ex["prompt"] for ex in out["examples"]}
    assert prompts == {"P1", "P3"}


# ── jsonl ────────────────────────────────────────────────────────────────────

def test_to_jsonl_emits_valid_json_lines():
    records = [
        _rec("P1", "a", True, rationale="r1"),
        _rec("P2", "b", True, rationale="r2"),
    ]
    out = harvest(records)
    text = to_jsonl(out)
    lines = text.splitlines()
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert set(obj) == {"prompt", "completion", "rationale"}
    # deterministic key order (sorted)
    assert lines[0].startswith('{"completion":')
