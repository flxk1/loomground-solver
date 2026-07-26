# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Methods of reasoning — an OPEN registry (rung 3, the rule-nD family).

The 5D algebra is fixed; the *methods* that reason over it are an open family,
plugged in like filters or rule-packs. Each method is named, tagged by kind, and
registered here. Shipped methods are drawn from six disciplines:

  * **logic** — modus ponens / tollens, hypothetical & disjunctive syllogism
    (:mod:`.inference`);
  * **philosophy** — abduction (inference to best explanation), analogical
    inference (:mod:`.inference`);
  * **methodology** (philosophy of science) — falsification, consistency /
    reductio (:mod:`.critique`);
  * **rationalist decision theory** — expected utility, maximin, maximax,
    Hurwicz, minimax-regret, satisficing (:mod:`.decide`);
  * **mathematics** — Pareto dominance, lexicographic ordering (:mod:`.decide`);
  * **data science** — Bayesian update, inductive generalization
    (:mod:`.inference`, :mod:`.decide`).

Kinds and their contract:
  * ``inference`` — ``f(facts, rules=()) -> {"facts": [lit], "rules": [Rule]}``:
    derive new literals/rules from what is given.
  * ``decision``  — ``f(options, payoffs, **kw) -> {"choice", "ranking", "scores"}``:
    pick within a set given valuations (closes the decision space deterministically).
  * ``test``      — ``f(...) -> {...}``: evaluate a hypothesis / consistency.

Register your own with :func:`register_method`. Pure stdlib."""
from __future__ import annotations

#: name -> (kind, fn)
METHODS: dict = {}

KINDS = ("inference", "decision", "test", "route")


def register_method(name: str, kind: str, fn) -> None:
    if kind not in KINDS:
        raise ValueError(f"unknown method kind {kind!r} (known: {KINDS})")
    METHODS[name] = (kind, fn)


def method(name: str):
    """The callable registered under ``name``."""
    return METHODS[name][1]


def methods_by_kind(kind: str) -> list:
    return sorted(n for n, (k, _fn) in METHODS.items() if k == kind)


# import the shipped families so they self-register
from . import inference   # noqa: E402,F401
from . import decide      # noqa: E402,F401
from . import critique    # noqa: E402,F401
from . import loomground  # noqa: E402,F401
