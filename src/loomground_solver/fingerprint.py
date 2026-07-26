# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Problem-solution fingerprint — an OPEN set of pluggable filters (lenses).

A fingerprint is a fixed-shape, comparable, signable summary of a problem-solution
pair. It is NOT a fixed list of layers: it is whatever set of *filters* you run.
Each filter is a lens that extracts one facet from the same ingredients (edges,
norms, the decided attack structure, the contract case). The engine is
filter-agnostic; filters are data, registered and composed like rule-packs or
render profiles — this is nD as an open family, not a closed schema.

Shipped filters (all domain-neutral):
  * ``logical_form``    — the closed-vocab histograms (5D edge dimensions; deontic
                          modalities). The *present relations*.
  * ``attack_topology`` — the shape of the deciding argument (from a DecisionSpace):
                          accepted / undecided / rejected, attacks, mutual
                          collisions, reinstatement. The *argumentative relations*.
  * ``negative_space``  — what is ABSENT but relevant: unfired defeaters,
                          untriggered exceptions, reported gaps.
  * ``argument_types``  — a histogram over argument-scheme tags (causal,
                          teleological, hierarchical, specialization, conflict,
                          deductive, …) inferred from dimensions + fired rules.
  * ``statistics``      — statistical descriptors: edge count, distinct dimensions,
                          Shannon entropy and concentration of the dimension
                          distribution, acceptance / undecided ratios.

Register your own with :func:`register_filter` — e.g. a domain filter for
mathematical structure, rhetoric, citation shape. ``distance`` compares over the
shared facets (each filter may bring its own comparator; otherwise a generic
histogram/set comparator is used) — a CHEAP recall filter, never a trust signal.
Version-mismatched fingerprints are INCOMPARABLE and raise (panel A2). Pure stdlib."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Callable, Optional

from .dimensions import Dimension

FP_VERSION = "fp-2"

_DIMS = tuple(d.value for d in Dimension)
_DEONTIC = ("obligatory", "permitted", "prohibited")


# ── filter registry ──────────────────────────────────────────────────────────

@dataclass
class Filter:
    """A named lens: ``extract(ctx) -> facet dict``, optional ``compare(fa, fb)
    -> float in [0,1]`` (defaults to the generic comparator)."""
    name: str
    extract: Callable[[dict], dict]
    compare: Optional[Callable[[dict, dict], float]] = None


FILTERS: dict = {}


def register_filter(name: str, extract, compare=None) -> None:
    """Register a fingerprint filter. Overrides an existing name."""
    FILTERS[name] = Filter(name, extract, compare)


# ── shared helpers ───────────────────────────────────────────────────────────

def _get(obj, key, default=""):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _dim_histogram(pairs) -> dict:
    h = {d: 0 for d in _DIMS}
    for p in pairs or []:
        for e in (_get(p, "edges", []) or []):
            dv = _get(e, "dimension", None)
            if dv in h:
                h[dv] += 1
    return h


# ── shipped filters ──────────────────────────────────────────────────────────

def _logical_form(ctx: dict) -> dict:
    deo = {d: 0 for d in _DEONTIC}
    for nrm in ctx.get("norms") or []:
        d = _get(nrm, "deontic", None)
        if d in deo:
            deo[d] += 1
    return {"dimensions": _dim_histogram(ctx.get("pairs")), "deontic": deo}


def _attack_topology(ctx: dict):
    dec = ctx.get("decision")
    if dec is None:
        return None
    atk = set(tuple(a) for a in dec.attacks)
    mutual = sum(1 for (a, b) in atk if (b, a) in atk) // 2
    reinstated = sum(1 for n in dec.accepted if any(t == n for (_s, t) in atk))
    return {"accepted": len(dec.accepted), "undecided": len(dec.undecided),
            "rejected": len(dec.rejected), "attacks": len(atk),
            "mutual_attacks": mutual, "reinstated": reinstated,
            "choice_required": bool(dec.undecided)}


def _negative_space(ctx: dict) -> dict:
    pack, fired, case = ctx.get("pack"), ctx.get("fired_rules"), ctx.get("case")
    unfired = []
    if pack is not None:
        fset = set(fired or [])
        unfired = sorted(o.name for o in pack.orderings if o.name not in fset)
    untriggered, gaps = [], []
    if case:
        gaps = sorted(case.get("gaps", []) or [])
        chain_text = " ".join(
            (str(s.get("text", "")) + " " + str(s.get("warrant", ""))).lower()
            for s in (case.get("chain", []) or []))
        for g in (case.get("grounds", []) or []):
            exc = (g.get("exception") or "").strip()
            if exc and exc[:20].lower() not in chain_text:
                untriggered.append(exc[:60])
    return {"unfired_defeaters": unfired,
            "untriggered_exceptions": sorted(set(untriggered)), "gaps": gaps}


_ARGUMENT_TYPES = ("causal", "teleological", "temporal", "mereological",
                   "associative", "hierarchical", "specialization",
                   "temporal-priority", "conflict", "deductive")
_DIM_TO_SCHEME = {"causal": "causal", "intentional": "teleological",
                  "temporal": "temporal", "structural": "mereological",
                  "relational": "associative"}
_RULE_TO_SCHEME = {"lex-superior": "hierarchical", "lex-specialis": "specialization",
                   "lex-posterior": "temporal-priority"}


def _argument_types(ctx: dict) -> dict:
    tags = {t: 0 for t in _ARGUMENT_TYPES}
    for p in ctx.get("pairs") or []:
        for e in (_get(p, "edges", []) or []):
            s = _DIM_TO_SCHEME.get(_get(e, "dimension", None))
            if s:
                tags[s] += 1
    for r in ctx.get("fired_rules") or []:
        s = _RULE_TO_SCHEME.get(r)
        if s:
            tags[s] += 1
    dec = ctx.get("decision")
    if dec is not None:
        if getattr(dec, "undecided", None):
            tags["conflict"] += 1
        if getattr(dec, "accepted", None) and not getattr(dec, "undecided", None):
            tags["deductive"] += 1
    return tags


_NEG_PREDICATES = frozenset({
    "not", "no", "never", "prohibits", "prohibit", "forbids", "forbid",
    "blocks", "block", "prevents", "prevent", "negates", "negate",
    "excludes", "exclude", "denies", "deny", "reduces", "reduce",
    "worsens", "worsen", "degrades", "degrade", "removes", "remove",
})


def _polarity(e) -> int:
    """Sign of a force: +1 unless the edge is explicitly negative. Domain-neutral —
    read an explicit ``polarity`` (bool / number / word), else a negating predicate."""
    pol = _get(e, "polarity", None)
    if isinstance(pol, bool):
        return 1 if pol else -1
    if isinstance(pol, (int, float)):
        return 1 if pol >= 0 else -1
    if isinstance(pol, str):
        pl = pol.strip().lower()
        if pl in ("-", "neg", "negative", "minus", "con", "against"):
            return -1
        if pl in ("+", "pos", "positive", "plus", "pro", "for"):
            return 1
    pred = str(_get(e, "predicate", "")).lower()
    if pred in _NEG_PREDICATES or pred.startswith("not_") or pred.startswith("non_"):
        return -1
    return 1


def _edges(ctx) -> list:
    return [e for p in (ctx.get("pairs") or []) for e in (_get(p, "edges", []) or [])]


def _contradiction(ctx: dict) -> dict:
    """Abstract the problem to its domain-neutral CONTRADICTION: opposing forces
    (opposite polarity) acting on a shared node — Altshuller's technical
    contradiction / Gentner's structural invariant. The *shape* coordinates
    (``contradiction_count``, ``tradeoff``, ``same_dimension_tension``) are
    dimension-agnostic and therefore transfer ACROSS DOMAINS: a legal
    disclosure-vs-privacy trade-off and a physics strength-vs-flexibility
    trade-off reduce to the same invariant. The per-dimension ``dimension_tension``
    histogram stays domain-specific — sharp within a domain, escalating across it.

    This is #2: fingerprint the contradiction, not the surface, so an unknown
    problem can be solved by the structural shape of a solution from another
    domain."""
    contended: dict = {}
    for e in _edges(ctx):
        node = _get(e, "object", "") or _get(e, "subject", "")
        contended.setdefault(node, []).append(
            (_get(e, "dimension", None), _polarity(e)))
    tension = {d: 0 for d in _DIMS}
    tradeoff_axes: set = set()
    same_dim = tradeoff = 0
    for _node, forces in contended.items():
        pos = [d for d, p in forces if p > 0]
        neg = [d for d, p in forces if p < 0]
        for dp in pos:
            for dn in neg:
                if dp == dn:
                    same_dim += 1
                    if dp in tension:
                        tension[dp] += 1
                else:
                    tradeoff += 1
                    tradeoff_axes.add("|".join(sorted((str(dp), str(dn)))))
    return {"contradiction_count": same_dim + tradeoff,
            "same_dimension_tension": same_dim,
            "tradeoff": tradeoff,
            "dimension_tension": tension,
            "tradeoff_axes": sorted(tradeoff_axes)}


def _statistics(ctx: dict) -> dict:
    dims = _dim_histogram(ctx.get("pairs"))
    total = sum(dims.values())
    distinct = sum(1 for v in dims.values() if v > 0)
    ent_norm = 0.0
    if total:
        ent = -sum((v / total) * math.log(v / total, 2) for v in dims.values() if v)
        maxent = math.log(distinct, 2) if distinct > 1 else 0.0
        ent_norm = ent / maxent if maxent else 0.0
    concentration = (max(dims.values()) / total) if total else 0.0
    dec = ctx.get("decision")
    acc = len(getattr(dec, "accepted", []) or []) if dec is not None else 0
    und = len(getattr(dec, "undecided", []) or []) if dec is not None else 0
    rej = len(getattr(dec, "rejected", []) or []) if dec is not None else 0
    tot = acc + und + rej
    return {"edges": total, "distinct_dimensions": distinct,
            "dimension_entropy": round(ent_norm, 4),
            "dimension_concentration": round(concentration, 4),
            "acceptance_ratio": round(acc / tot, 4) if tot else 0.0,
            "undecided_ratio": round(und / tot, 4) if tot else 0.0}


def _adapter_context(ctx: dict) -> Optional[dict]:
    """Lossless typed nD coordinates emitted by universal system adapters."""
    if not ctx.get("adapter_coordinates"):
        return None
    by_system: dict[str, dict[str, list]] = {}
    for coordinate in ctx.get("adapter_coordinates") or ():
        system = f"{coordinate['system']}@{coordinate['version']}"
        axis = str(coordinate["axis"])
        by_system.setdefault(system, {}).setdefault(axis, []).append(
            coordinate.get("value"))
    return {
        system: {axis: sorted(values, key=repr)
                 for axis, values in sorted(axes.items())}
        for system, axes in sorted(by_system.items())
    }


register_filter("logical_form", _logical_form)
register_filter("attack_topology", _attack_topology)
register_filter("negative_space", _negative_space)
register_filter("argument_types", _argument_types)
register_filter("statistics", _statistics)
register_filter("contradiction", _contradiction)
register_filter("adapter_context", _adapter_context)


# ── build + compare + sign ───────────────────────────────────────────────────

def fingerprint(*, filters=None, pairs=None, norms=None, pack=None,
                fired_rules=None, decision=None, case=None,
                adapter_coordinates=None) -> dict:
    """Compute a fingerprint by running ``filters`` (default: all registered) over
    the supplied ingredients. Returns ``{version, facets: {name: facet}}``."""
    ctx = {"pairs": pairs, "norms": norms, "pack": pack,
           "fired_rules": fired_rules, "decision": decision, "case": case,
           "adapter_coordinates": adapter_coordinates}
    names = list(filters) if filters is not None else list(FILTERS)
    return {"version": FP_VERSION,
            "facets": {n: FILTERS[n].extract(ctx) for n in names if n in FILTERS}}


def _l1_norm(a: list, b: list) -> float:
    den = sum(a) + sum(b)
    return (sum(abs(x - y) for x, y in zip(a, b)) / den) if den else 0.0


def _flatten(d, prefix=""):
    """Split a facet into aligned numeric leaves and a token set (for lists/strs)."""
    nums, toks = {}, set()
    if not isinstance(d, dict):
        return nums, toks
    for k, v in d.items():
        p = f"{prefix}/{k}"
        if isinstance(v, bool):
            nums[p] = 1.0 if v else 0.0
        elif isinstance(v, (int, float)):
            nums[p] = float(v)
        elif isinstance(v, str):
            toks.add(f"{p}={v}")
        elif isinstance(v, (list, tuple, set)):
            for x in v:
                toks.add(f"{p}~{x}")
        elif isinstance(v, dict):
            n2, t2 = _flatten(v, p)
            nums.update(n2)
            toks |= t2
    return nums, toks


def _auto_compare(fa: dict, fb: dict) -> float:
    """Generic facet distance in [0,1]: L1 over aligned numeric leaves + Jaccard
    over token leaves, averaged over whichever components are present."""
    na, ta = _flatten(fa)
    nb, tb = _flatten(fb)
    comps = []
    keys = set(na) | set(nb)
    if keys:
        comps.append(_l1_norm([na.get(k, 0.0) for k in keys],
                              [nb.get(k, 0.0) for k in keys]))
    union = ta | tb
    if union:
        comps.append(1.0 - len(ta & tb) / len(union))
    return sum(comps) / len(comps) if comps else 0.0


def distance(a: dict, b: dict, *, weights=None) -> float:
    """Cheap recall-filter distance in [0,1] over the SHARED facets (each via its
    filter's comparator, or the generic one). ``weights``: optional
    ``{facet_name: weight}``. Version mismatch is incomparable and raises (A2)."""
    if a.get("version") != b.get("version"):
        raise ValueError(f"incomparable fingerprints: {a.get('version')} vs "
                         f"{b.get('version')} — declare a migration first")
    fa, fb = a.get("facets", {}), b.get("facets", {})
    shared = [n for n in fa if n in fb and fa[n] is not None and fb[n] is not None]
    if not shared:
        return 0.0
    total = wsum = 0.0
    for n in shared:
        w = (weights or {}).get(n, 1.0)
        cmp = (FILTERS[n].compare if n in FILTERS and FILTERS[n].compare
               else _auto_compare)
        total += w * cmp(fa[n], fb[n])
        wsum += w
    return max(0.0, min(1.0, total / wsum)) if wsum else 0.0


def canonical_bytes(fp: dict) -> bytes:
    return json.dumps(fp, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def signature(fp: dict) -> str:
    """Content address of a fingerprint (federation identity + dedup)."""
    return "sha256:" + hashlib.sha256(canonical_bytes(fp)).hexdigest()
