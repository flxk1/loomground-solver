# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Case registry — discover the CaseSpecs the fleet drops into ``cases/``.

The convention is deliberately flat so a sub-session just *adds a file*: under
``cases/statutes/`` · ``cases/contracts/`` · ``cases/policies/`` (and
``cases/probes/`` for adversarial fabrication probes), each ``*.py`` module
exposes its case(s) as a module global — a :class:`CaseSpec` named ``CASE``, or
a list/tuple named ``CASES``. :func:`collect_cases` imports every such module and
returns the union.

No registration call, no decorator, no central manifest to edit — discovery is
by import + duck-typing on the module globals. A module that fails to import, or
exposes no case, is reported (not silently swallowed) so a broken case can't
vanish from the panel.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import List, Tuple

from . import cases as _cases_pkg
from .case_spec import CaseSpec

__all__ = ["collect_cases", "collect_cases_by_kind", "discover_case_modules"]


def discover_case_modules() -> List[str]:
    """Every importable module under the ``cases`` package (recursively)."""
    names: List[str] = []
    for info in pkgutil.walk_packages(_cases_pkg.__path__,
                                      prefix=_cases_pkg.__name__ + "."):
        if info.ispkg:
            continue
        names.append(info.name)
    return sorted(names)


def _cases_in_module(mod) -> List[CaseSpec]:
    found: List[CaseSpec] = []
    case = getattr(mod, "CASE", None)
    if isinstance(case, CaseSpec):
        found.append(case)
    for item in (getattr(mod, "CASES", None) or []):
        if isinstance(item, CaseSpec):
            found.append(item)
    # Fallback: any module-global CaseSpec (so a bare `gdpr = CaseSpec(...)`
    # is still discovered), de-duplicated by identity.
    for name, val in vars(mod).items():
        if isinstance(val, CaseSpec) and val not in found:
            found.append(val)
    return found


def collect_cases() -> Tuple[CaseSpec, ...]:
    """Import every case module and return all discovered CaseSpecs.

    Case ids must be unique across the whole registry; a collision raises (two
    files claiming the same id is an authoring error, not something to resolve
    silently).
    """
    collected: List[CaseSpec] = []
    seen_ids: dict[str, str] = {}
    for modname in discover_case_modules():
        mod = importlib.import_module(modname)
        for spec in _cases_in_module(mod):
            if spec.id in seen_ids:
                raise ValueError(
                    f"duplicate case id {spec.id!r}: {modname} vs "
                    f"{seen_ids[spec.id]}")
            seen_ids[spec.id] = modname
            collected.append(spec)
    return tuple(collected)


def collect_cases_by_kind() -> dict:
    """The collected cases bucketed by ``case_kind`` — the shape S5 rolls up."""
    out: dict = {}
    for spec in collect_cases():
        out.setdefault(spec.case_kind, []).append(spec)
    return out
