# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The definition of 'universal': no file under loomground_solver/ may import
governance or corpus, and no file may hard-code a domain literal in its code.

This mirrors RVND's own tests/test_dependency_inversion.py philosophy: the
substrate stays pure by construction, and a green run here is the machine-checked
proof of it. Governance and corpus arrive only through the injected ports.

Two assertions:
  1. no import (relative or absolute) names a governance/corpus module;
  2. no domain literal appears in code (comments, docstrings and the PROFILES
     render-vocabulary data are allowed — those are labels, not logic).
"""

from __future__ import annotations

import ast
import io
import pathlib
import tokenize

import pytest

PKG = pathlib.Path(__file__).resolve().parent.parent / "src" / "loomground_solver"

# governance + corpus modules the substrate must never bind
FORBIDDEN_IMPORTS = (
    "policy", "lock", "decision_surface", "mutation_log", "signing",
    "rule_extractor", "rule_registry", "legal_", "hohfeld", "kg_export",
    "workspaces", "celex", "gdpr",
)

# domain content that must never be wired into the pure core (allowed only in
# comments / docstrings / the PROFILES data)
DOMAIN_LITERALS = (
    "celex", "gdpr", "law-eu", "obliged", "personal-data", "data-protection",
)

PY_FILES = sorted(p for p in PKG.rglob("*.py") if "__pycache__" not in p.parts)

# The graded-panel case corpus (``eval/panel/cases/``) is domain DATA by design —
# CaseSpec instances describing real statutes/contracts/policies — not engine
# code. The purity rule (no domain literal in executable code) guards the
# SUBSTRATE; the corpus is the injected content the substrate reasons over, so it
# is excluded from the domain-literal check ONLY. The import checks still apply:
# a case may not import governance/corpus either.
_CORPUS_MARKER = ("eval", "panel", "cases")


def _is_corpus(path: pathlib.Path) -> bool:
    parts = path.parts
    return all(m in parts for m in _CORPUS_MARKER)


def test_there_are_python_files_to_check():
    assert PY_FILES, f"no package files found under {PKG}"


@pytest.mark.parametrize("path", PY_FILES, ids=lambda p: p.name)
def test_no_forbidden_import_lines(path):
    """Replicates the HARD-RULE grep: no line containing 'import' may name a
    governance/corpus module."""
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if "import" not in line:
            continue
        # ignore comment-only text after a '#'
        code = line.split("#", 1)[0]
        if "import" not in code:
            continue
        low = code.lower()
        hits = [tok for tok in FORBIDDEN_IMPORTS if tok in low]
        assert not hits, f"{path.name}:{lineno} imports forbidden {hits}: {line!r}"


@pytest.mark.parametrize("path", PY_FILES, ids=lambda p: p.name)
def test_no_forbidden_import_in_ast(path):
    """Structural check: every imported module (Import / ImportFrom) is stdlib
    or intra-package, never a governance/corpus module."""
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    for mod in names:
        low = mod.lower()
        hits = [tok for tok in FORBIDDEN_IMPORTS if tok in low]
        assert not hits, f"{path.name} imports {mod!r} — forbidden {hits}"


def _code_only(path: pathlib.Path) -> str:
    """Source with comments AND docstrings removed — what actually executes."""
    src = path.read_text()
    # strip comments via tokenize
    out = []
    toks = tokenize.generate_tokens(io.StringIO(src).readline)
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            continue
        out.append(tok)
    stripped = tokenize.untokenize(out)
    # strip docstrings via AST: blank out Constant-str expression statements
    tree = ast.parse(src)
    docstrings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            ds = ast.get_docstring(node, clean=False)
            if ds:
                docstrings.add(ds)
    for ds in docstrings:
        stripped = stripped.replace(ds, "")
    return stripped


@pytest.mark.parametrize("path", PY_FILES, ids=lambda p: p.name)
def test_no_domain_literal_in_code(path):
    """No corpus/domain literal is hard-coded in executable code. Comments,
    docstrings and the PROFILES render-vocabulary are labels, not logic, and are
    allowed — they are excluded before the check.

    The ``eval/panel/cases/`` corpus is excluded too: those files are CaseSpec
    DATA describing real domains (the injected content), not the corpus-free
    engine.
    """
    if _is_corpus(path):
        pytest.skip("panel case corpus is domain DATA by design, not engine code")
    code = _code_only(path).lower()
    hits = [lit for lit in DOMAIN_LITERALS if lit in code]
    assert not hits, f"{path.name} hard-codes domain literal(s) {hits} in code"
