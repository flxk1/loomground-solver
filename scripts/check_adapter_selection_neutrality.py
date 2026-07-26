#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Universality gate: adapter *selection* carries no vendor-name special-casing.

Solver's adapter boundary (``src/loomground_solver/adapters/``) lets any system
implement ``SystemAdapter`` and register through ``AdapterRegistry``. The
selection modules — ``registry.py`` (how an adapter is looked up),
``protocol.py`` (what an adapter must implement), and ``models.py`` (the
records an adapter emits) — must select and describe adapters solely by the
neutral ``SystemIdentity`` contract, never by branching on which vendor
happens to be asking.

This script AST-scans those three modules for a string-literal constant whose
value, case-insensitively, exactly equals a known vendor/product name
(``versum``, ``solver``). An occurrence there would mean a selection module
special-cases a particular implementation instead of treating every
conforming adapter alike; a match fails the check. A vendor naming *itself* in
its own adapter module (for example ``versum.py`` declaring
``loomground.versum.claim-axes/v1`` as its own schema identifier) is outside
this check's scope — that is an adapter declaring its own identity, not a
selection module choosing one adapter over another.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTERS_DIR = ROOT / "src" / "loomground_solver" / "adapters"

SELECTION_MODULES = ("registry.py", "protocol.py", "models.py")
BANNED_LITERALS = frozenset({"versum", "solver"})


def _string_constants(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node


def check_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = []
    for node in _string_constants(tree):
        if node.value.strip().lower() in BANNED_LITERALS:
            violations.append(
                f"{path.relative_to(ROOT)}:{node.lineno}: vendor-name literal "
                f"{node.value!r} in a selection module"
            )
    return violations


def main() -> int:
    violations: list[str] = []
    for name in SELECTION_MODULES:
        path = ADAPTERS_DIR / name
        if not path.is_file():
            violations.append(f"expected selection module missing: {path}")
            continue
        violations.extend(check_file(path))

    if violations:
        for violation in violations:
            print(f"[FAIL] {violation}")
        return 1

    print(
        "adapter selection neutrality ok: "
        f"{', '.join(SELECTION_MODULES)} carry no vendor-name special-casing"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
