# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Reasoning in fingerprint space — narrow an unknown problem's solution by
INFERENCE over a federation of problem→solution fingerprint pairs. Not retrieval.

The federation is a body of problem→solution fingerprint *pairs*. The regularity
across them is a **structural transform**: for each coordinate of the fingerprint,
how the solution's structure differs from the problem's. Given a new problem's
fingerprint, the transform DERIVES the target solution's coordinates — wherever the
federation agrees. Where it disagrees, that coordinate is UNDETERMINED: the
structure does not pin it down, so it ESCALATES rather than being guessed (the
grounded discipline, carried into fingerprint space).

There is no nearest neighbour and nothing is copied from a single case. The target
is composed from the WHOLE federation's structural regularity. The derived
fingerprint is a *constraint* on the solution — what structure a solution must
have — which the solver's contract / decision layer then verifies or fills.

Two kinds of coordinate, reasoned over together:

  * **Numeric** coordinates (histograms, topology counts, and the *cardinality* of
    every set-valued leaf, keyed ``…#n``). These are the cross-domain-transferable
    structural signal: "the solution closes exactly one gap", "adds one causal
    edge". A count delta can be agreed on even when the domains are unrelated.

  * **Set-valued** coordinates — the NEGATIVE SPACE: which specific defeaters,
    exceptions and gaps a solution closes or opens. Their *identity* is domain-
    bound, so the federation only pins one down when it SYSTEMATICALLY agrees
    (every solution closes the same gap). Otherwise the count transfers and the
    identity escalates. Negative space is the sharp discriminator — two problems
    are alike not only in what is present but in what is absent.

Pure stdlib."""
from __future__ import annotations

UNDETERMINED = None


def _versions(*fps):
    return {fp.get("version") for fp in fps}


def _walk(d, prefix=""):
    """Split a facet into numeric leaves (bool/int/float) and set-valued leaves
    (list/tuple/set/str members), each keyed by its path."""
    nums: dict = {}
    sets: dict = {}
    if not isinstance(d, dict):
        return nums, sets
    for k, v in d.items():
        p = f"{prefix}/{k}"
        if isinstance(v, bool):
            nums[p] = 1.0 if v else 0.0
        elif isinstance(v, (int, float)):
            nums[p] = float(v)
        elif isinstance(v, str):
            sets[p] = frozenset({v})
        elif isinstance(v, (list, tuple, set)):
            sets[p] = frozenset(str(x) for x in v)
        elif isinstance(v, dict):
            n2, s2 = _walk(v, p)
            nums.update(n2)
            sets.update(s2)
    return nums, sets


def _coords(fp: dict):
    """Flatten a whole fingerprint to ``(numeric, sets)``. Every set-valued leaf
    also contributes a ``<path>#n`` cardinality into the numeric coordinates — the
    cross-domain structural signal (how many defeaters/gaps), distinct from the
    domain-bound identity of the members."""
    nums: dict = {}
    sets: dict = {}
    for name, facet in (fp.get("facets") or {}).items():
        if facet is None:
            continue
        n, s = _walk(facet, name)
        nums.update(n)
        sets.update(s)
    for path, members in sets.items():
        nums[f"{path}#n"] = float(len(members))
    return nums, sets


def _facet_names(fp: dict) -> frozenset:
    """The coordinate SHAPE of a fingerprint: the names of its non-None facets
    (a None facet — e.g. attack_topology with no decision — contributes no
    coordinate, so it is excluded)."""
    return frozenset(n for n, f in (fp.get("facets") or {}).items() if f is not None)


def _check_pairs(pairs):
    vs = set()
    shapes = set()
    for p, s in pairs:
        vs |= _versions(p, s)
        shapes.add(_facet_names(p))
        shapes.add(_facet_names(s))
    if len(vs) > 1:
        raise ValueError(f"incomparable fingerprints across the federation: {vs} "
                         f"— declare a migration before deriving (A2)")
    if len(shapes) > 1:
        raise ValueError(
            "incomparable fingerprint SHAPES across the federation: "
            f"{sorted(sorted(s) for s in shapes)} — a problem, its solution, and "
            "every pair must share the same facet set, else a facet present on one "
            "side and absent on the other is silently read as zero and reported as "
            "a determined delta (A2)")


def structural_transform(pairs, *, tol: float = 1e-9) -> dict:
    """The problem→solution transform learned from the federation. Returns
    ``{coordinate: value}`` where value is:

      * a ``float`` delta for a numeric coordinate the federation AGREES on;
      * ``{"add": frozenset, "remove": frozenset}`` for a set coordinate the
        federation SYSTEMATICALLY agrees on (same members added/removed everywhere);
      * ``UNDETERMINED`` (``None``) where the federation disagrees — the structure
        is not pinned, so it escalates rather than being guessed.

    A coordinate seen in only some pairs still counts; disagreement is what makes
    it undetermined."""
    if not pairs:
        return {}
    _check_pairs(pairs)
    num_deltas: dict = {}
    set_deltas: dict = {}
    for problem_fp, solution_fp in pairs:
        pn, ps = _coords(problem_fp)
        sn, ss = _coords(solution_fp)
        for k in set(pn) | set(sn):
            num_deltas.setdefault(k, []).append(sn.get(k, 0.0) - pn.get(k, 0.0))
        for k in set(ps) | set(ss):
            pv, sv = ps.get(k, frozenset()), ss.get(k, frozenset())
            set_deltas.setdefault(k, []).append((sv - pv, pv - sv))  # (added, removed)
    transform: dict = {}
    for k, ds in num_deltas.items():
        transform[k] = ds[0] if (max(ds) - min(ds)) <= tol else UNDETERMINED
    for k, ds in set_deltas.items():
        added = {a for a, _ in ds}
        removed = {r for _, r in ds}
        if len(added) == 1 and len(removed) == 1:
            (a,), (r,) = added, removed
            transform[k] = {"add": a, "remove": r}
        else:
            transform[k] = UNDETERMINED
    return transform


def derive_solution(problem_fp: dict, pairs, *, tol: float = 1e-9) -> dict:
    """Narrow the solution of ``problem_fp`` by applying the federation's structural
    transform. Returns:

      * ``determined``      — numeric coordinates the federation pins down;
      * ``determined_sets`` — set coordinates (negative space) it pins down, as the
        derived member list ``(problem_set − removed) ∪ added``;
      * ``undetermined``    — coordinates it does not pin (these escalate — a
        human/LLM or a further method decides them);
      * ``determinacy``     — the share of coordinates pinned down.

    This is narrowing-as-inference: the answer's structure is composed from the
    whole federation, not fetched from a neighbour."""
    if pairs:
        if problem_fp.get("version") not in _versions(pairs[0][0]):
            raise ValueError("problem fingerprint version differs from the "
                             "federation — incomparable (A2)")
        if _facet_names(problem_fp) != _facet_names(pairs[0][0]):
            raise ValueError("problem fingerprint SHAPE differs from the federation "
                             "— its facet set must match, else missing coordinates "
                             "are silently derived from zero (A2)")
    transform = structural_transform(pairs, tol=tol)
    pn, ps = _coords(problem_fp)
    determined: dict = {}
    determined_sets: dict = {}
    undetermined: list = []
    for k, delta in transform.items():
        if delta is UNDETERMINED:
            undetermined.append(k)
        elif isinstance(delta, dict):                       # a set coordinate
            base = ps.get(k, frozenset())
            derived = (base - delta["remove"]) | delta["add"]
            determined_sets[k] = sorted(derived)
        else:                                               # a numeric coordinate
            determined[k] = round(pn.get(k, 0.0) + delta, 6)
    total = len(determined) + len(determined_sets) + len(undetermined)
    pinned = len(determined) + len(determined_sets)
    return {"determined": determined,
            "determined_sets": determined_sets,
            "undetermined": sorted(undetermined),
            "determinacy": round(pinned / total, 6) if total else 0.0}
