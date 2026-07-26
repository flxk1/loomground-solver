# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The product surface — thin conveniences over the verbatim internals.

Three entry points cover the package's job:

  * ``entail`` — compose multi-hop inferences over a set of dimensioned pairs;
  * ``plan``   — validate a derived solver topology and return its order + graph;
  * ``check``  — run the reasoning contract over a case, taking oversight from
                 an injected ``Governance`` (``NullGovernance`` by default).

Signatures are deliberately permissive; the verbatim internals
(:mod:`reasoning`, :mod:`topology`, :mod:`contract`) remain the precise API.
"""

from __future__ import annotations

from typing import Any, Optional

from . import contract as _contract
from . import reasoning as _reasoning
from . import topology as _topology
from .federation import derive_solution as _derive_solution
from .ports import Governance, NullGovernance


def entail(pairs, subject: Optional[str] = None, *, max_hops: int = 4):
    """Compose inferences from dimensioned ``pairs``.

    Thin wrapper over :func:`reasoning.extract_edges` + :func:`reasoning.compose_paths`.
    ``subject`` pins the start node (None = every node); ``max_hops`` bounds the
    path depth. Returns a list of :class:`reasoning.Inference`, highest
    confidence first."""
    edges = _reasoning.extract_edges(pairs)
    return _reasoning.compose_paths(edges, start=subject, max_depth=max_hops)


def plan(nodes, deps, *, roots=None) -> dict[str, Any]:
    """Validate a derived solver topology and, if clean, project it.

    Thin wrapper over :func:`topology.build_topology`: returns ``{ok, findings,
    order, graph}``."""
    return _topology.build_topology(nodes, deps, roots=roots)


def narrow(problem_fp: dict, federation, *, tol: float = 1e-9) -> dict:
    """Narrow the solution of an UNKNOWN problem by inference over a ``federation``
    of problem→solution fingerprint pairs — reasoning in fingerprint space, not
    retrieval. The answer's structure is composed from the whole federation's
    regularity; nothing is fetched from a neighbour.

    Returns the decision-space carried into fingerprint space:

      * ``solution``    — the derived structure the federation pins down (the
                          accepted, auto-derivable coordinates: numeric + set-valued
                          negative space);
      * ``escalate``    — the coordinates it does NOT pin down; the bounded set a
                          decision-maker (human / LLM / a further method) must
                          resolve, and cannot step outside. Undetermined structure
                          escalates — it is never guessed;
      * ``determinacy`` — the share of coordinates pinned down;
      * ``complete``    — whether the federation pinned the whole structure.

    Thin wrapper over :func:`federation.derive_solution`."""
    d = _derive_solution(problem_fp, federation, tol=tol)
    # `complete` requires the WHOLE structure pinned (determinacy 1.0), not merely
    # "nothing escalated" — an empty/zero-knowledge federation escalates nothing yet
    # pins nothing, and must NOT read as complete.
    return {"solution": {**d["determined"], **d["determined_sets"]},
            "escalate": d["undetermined"],
            "determinacy": d["determinacy"],
            "complete": d["determinacy"] == 1.0}


def check(case: dict, *, governance: Governance = NullGovernance(), **kw):
    """Run the reasoning contract over ``case``.

    Wrapper over :func:`contract.check_case`. Oversight parameters default to the
    injected ``governance`` (``oversight_level`` / ``oversight_active``); an
    explicit keyword overrides. ``classify`` defaults to ``governance.classify``
    but is not required by ``check_case`` and is dropped for it. Any other
    keyword (``stake``, ``personal``, ``held_pinpoints``) passes straight
    through."""
    kw.setdefault("oversight_level", governance.oversight_level())
    kw.setdefault("oversight_active", governance.oversight_active())
    kw.setdefault("classify", governance.classify)
    # check_case does not consume a classifier (that is check_export's port);
    # keep the surface permissive by not forwarding it.
    kw.pop("classify", None)
    return _contract.check_case(case, **kw)
