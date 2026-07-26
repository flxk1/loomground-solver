#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Writing-register gate.

Durable artifacts (code, tests, docs, comments) address the maintainer who
reads them a year from now, not the build session that produced them. This
script enforces that register on every tracked ``*.py`` and ``*.md`` file by
failing on lines that carry:

- a plan/milestone citation (``SOLVER-PLAN``, ``VERSUM-PLAN``, ``RVND-PLAN``,
  a bare ``loomground-ref``, a ``J<n>-ratified`` label, or a ``ruling X'``
  citation) instead of stating the invariant itself;
- a private fork path (``flxk1/solver``, ``flxk1/versum``, or a
  ``github.com/flxk1/loomground`` reference) instead of the published repo;
- a reference to "this chat", "this session", or a "sibling session";
- an AI co-author commit trailer;
- a bare commit-hash citation instead of the rule the commit encoded.

It does not flag legitimate technical terms, frozen contract/version strings,
or vendored fixture corpora (see ``EXCLUDED_DIRS`` / ``EXCLUDED_PATH_PARTS``
below).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

EXCLUDED_DIRS = ("LICENSES/", "build/", "dist/")
EXCLUDED_PATH_PARTS = ("/fixtures/", "claim_axes_vectors")

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("plan citation", re.compile(r"\b(?:SOLVER|VERSUM|RVND)-PLAN\b")),
    ("plan citation", re.compile(r"\bloomground-ref\b")),
    ("private fork path", re.compile(r"flxk1/solver\b")),
    ("private fork path", re.compile(r"flxk1/versum\b")),
    ("private fork path", re.compile(r"github\.com/flxk1/loomground(?![-\w])")),
    ("ratification label", re.compile(r"\bJ\d+-ratified\b")),
    ("ruling citation", re.compile(r"\bruling [A-Z][′'´]")),
    ("session reference", re.compile(r"\bthis (?:chat|session)\b")),
    ("session reference", re.compile(r"\bsibling session\b")),
    ("AI co-author trailer",
     re.compile(r"Co-Authored-By:\s*.*(?:Claude|Anthropic)")),
    ("commit-hash citation", re.compile(r"\bcommit [0-9a-f]{7,40}\b")),
]


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--", "*.py", "*.md"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _is_excluded(rel_path: str) -> bool:
    if (ROOT / rel_path).resolve() == SELF:
        return True
    if any(rel_path.startswith(prefix) for prefix in EXCLUDED_DIRS):
        return True
    if any(part in rel_path for part in EXCLUDED_PATH_PARTS):
        return True
    return False


def main() -> int:
    hits: list[str] = []
    for rel_path in _tracked_files():
        if _is_excluded(rel_path):
            continue
        path = ROOT / rel_path
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PATTERNS:
                match = pattern.search(line)
                if match:
                    hits.append(f"{rel_path}:{lineno}: [{label}] {match.group(0)!r}")

    if hits:
        for hit in hits:
            print(f"[FAIL] {hit}")
        print(f"{len(hits)} writing-register violation(s) found")
        return 1

    print("writing register ok: no plan/session/private-path citations found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
