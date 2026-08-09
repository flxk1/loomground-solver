# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Standing conformance gate — fails CI on consume-vs-regrow regressions.

This is NOT a behavioural test. It guards the *architecture* the package commits
to, so a future change (or a future build loop) that re-grows a canonical
primitive fails HERE, mechanically, instead of being caught by eye in a manual
audit. It codifies the four regrowth classes found and fixed on 2026-08-06:

  A. **one three-valued verdict vocabulary** — only ``cross_subsumption.Verdict``
     may carry the SATISFIED / NOT_SATISFIED / OPEN triad; no module mints a
     parallel one (the ``burden`` PROVEN/DISPROVEN/NON_LIQUET regression).
  B. **one confidence floor** — a single ``0.85`` literal, in the leaf
     ``predicate``; everything else aliases it.
  C. **one reachability walker** — reachability over ``reasoning.Edge`` goes
     through ``reasoning.compose_paths``; no hand-rolled BFS beside it (the
     ``cross_subsumption._reachable`` regression).
  D. **no orphans** — every top-level module is wired (exported or consumed) AND
     has test coverage.

When a check legitimately needs an exception, add it to the small allowlist next
to that check WITH a comment naming why — an explicit, reviewable decision, not a
silent skip. The denylists are meant to GROW as new clone shapes are spotted (see
the consume-modules standing-gate memory).
"""
from __future__ import annotations

import ast
import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "loomground_solver"
TESTS = pathlib.Path(__file__).resolve().parent


def _src_files() -> list[pathlib.Path]:
    """Every .py under src (recursive), excluding package __init__ files."""
    return [p for p in SRC.rglob("*.py") if p.name != "__init__.py"]


# ── A. one three-valued verdict vocabulary ─────────────────────────────────────

_VERDICT_VALUES = {"satisfied", "not_satisfied", "open"}

# Known verdict-triad NAME clones that must not reappear outside Verdict. This
# denylist is meant to grow when a new clone shape is spotted.
_VERDICT_NAME_CLONES = [
    {"SATISFIED", "NOT_SATISFIED", "OPEN"},   # only cross_subsumption.Verdict may carry these
    {"PROVEN", "DISPROVEN", "NON_LIQUET"},    # the burden regression (fixed 2026-08-06)
    {"MET", "UNMET", "OPEN"},
    {"PASS", "FAIL", "ESCALATE"},
    {"TRUE", "FALSE", "UNKNOWN"},
]


def _enum_defs(path: pathlib.Path):
    """Yield ``(class_name, {member: value_or_None})`` for each Enum-ish class."""
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {getattr(b, "id", getattr(b, "attr", "")) for b in node.bases}
        if not (bases & {"Enum", "IntEnum", "IntFlag", "Flag"}):
            continue
        members: dict[str, object] = {}
        for stmt in node.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                name = stmt.targets[0].id
                if name.startswith("_"):
                    continue
                members[name] = (stmt.value.value
                                 if isinstance(stmt.value, ast.Constant) else None)
        if members:
            yield node.name, members


def test_single_verdict_vocabulary():
    offenders: list[str] = []
    for path in _src_files():
        for cls, members in _enum_defs(path):
            canonical = (path.name == "cross_subsumption.py" and cls == "Verdict")
            if canonical:
                continue
            names = set(members)
            values = {v for v in members.values() if isinstance(v, str)}
            if _VERDICT_VALUES <= values:
                offenders.append(f"{path.name}:{cls} carries the Verdict value-set")
            for clone in _VERDICT_NAME_CLONES:
                if names == clone:
                    offenders.append(f"{path.name}:{cls} = {sorted(names)} is a Verdict clone")
    assert not offenders, (
        "Parallel three-valued verdict(s) found — consume cross_subsumption.Verdict "
        "instead of minting a new one:\n  " + "\n  ".join(offenders))


# ── B. one confidence floor ────────────────────────────────────────────────────

_FLOOR_LITERAL = re.compile(r"\b[A-Z_]*FLOOR[A-Z_]*\s*=\s*0\.[0-9]")


def test_single_confidence_floor():
    hits: list[str] = []
    for path in _src_files():
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if _FLOOR_LITERAL.search(line):
                hits.append(f"{path.relative_to(SRC)}:{i}: {line.strip()}")
    assert len(hits) == 1, (
        "Expected exactly ONE FLOOR float literal (the single source of truth); "
        "every other floor must alias it. Found:\n  " + "\n  ".join(hits))


# ── C. one reachability walker over reasoning.Edge ─────────────────────────────

_IMPORTS_EDGE = re.compile(r"from\s+\.reasoning\s+import\s+[^\n]*\bEdge\b")
_RAW_WALK = re.compile(r"\badjacency\b|\bfrontier\b|collections\.deque|\.pop\(0\)|def\s+walk\(")


def test_edge_reachability_consumes_compose_paths():
    offenders: list[str] = []
    for path in _src_files():
        if path.name == "reasoning.py":      # the definition site of compose_paths
            continue
        text = path.read_text()
        if _IMPORTS_EDGE.search(text) and _RAW_WALK.search(text) and "compose_paths" not in text:
            offenders.append(path.name)
    assert not offenders, (
        "Module(s) walk reasoning.Edge with a hand-rolled traversal instead of "
        "consuming reasoning.compose_paths:\n  " + "\n  ".join(offenders))


# ── D. no orphans: every top-level module wired AND tested ─────────────────────

# Excluded from the module census (not capability modules).
_SKIP = {"__init__.py", "__main__.py", "_version.py"}

# Façade modules covered INDIRECTLY (no dedicated test_<name>.py and only
# re-exported, never consumed by another src module — so the transitive-coverage
# clause below does not reach them — yet their symbols ARE exercised). Each entry
# is an explicit, reviewed decision naming where, so the claim stays checkable.
_INDIRECTLY_TESTED = {
    "api": "façade: plan/entail/check/narrow exercised via package-level imports "
           "in test_interpret.py & test_adapters.py",
}


def _toplevel_modules() -> list[pathlib.Path]:
    return [p for p in SRC.glob("*.py")
            if p.name not in _SKIP and not p.name.startswith("_")]


def _consumed_by_other_src(mod: str, src_texts: dict[str, str]) -> bool:
    """True iff a *functional* src module (not the package __init__) imports mod —
    so mod is exercised transitively whenever that consumer's tests run."""
    return any(name not in {f"{mod}.py", "__init__.py"}
               and re.search(rf"from\s+\.{re.escape(mod)}\s+import", t)
               for name, t in src_texts.items())


def _wired(mod: str, init_text: str, src_texts: dict[str, str]) -> bool:
    if re.search(rf"from\s+\.{re.escape(mod)}\s+import", init_text):
        return True                                    # re-exported by the package
    return _consumed_by_other_src(mod, src_texts)      # consumed by another src module


def _tested(mod: str, test_texts: str, src_texts: dict[str, str]) -> bool:
    if (TESTS / f"test_{mod}.py").exists():
        return True                                    # a dedicated behavioural test
    if mod in _INDIRECTLY_TESTED:
        return True                                    # explicit, reviewed exception
    if re.search(rf"loomground_solver\.{re.escape(mod)}\b"
                 rf"|from\s+\.{re.escape(mod)}\s+import", test_texts):
        return True                                    # named directly in a test
    return _consumed_by_other_src(mod, src_texts)      # exercised via its consumer's tests


def test_no_orphan_modules():
    init_text = (SRC / "__init__.py").read_text()
    src_texts = {p.name: p.read_text() for p in SRC.rglob("*.py")}
    test_texts = " ".join(p.read_text() for p in TESTS.glob("test_*.py"))
    unwired, untested = [], []
    for path in _toplevel_modules():
        mod = path.stem
        if not _wired(mod, init_text, src_texts):
            unwired.append(mod)
        if not _tested(mod, test_texts, src_texts):
            untested.append(mod)
    assert not unwired, ("Unwired (orphan) module(s) — not exported and not consumed: "
                         + ", ".join(sorted(unwired)))
    assert not untested, ("Untested module(s) — add a test_<name>.py or an explicit "
                          "_INDIRECTLY_TESTED entry naming the covering test: "
                          + ", ".join(sorted(untested)))
