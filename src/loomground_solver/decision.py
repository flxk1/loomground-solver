# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The decision space — the deterministic bounded set an automatic decision-maker
pulls from (rung 4).

Given candidate solutions, this computes the grounded extension of their attack
graph and returns three sets:

  * **accepted** — grounded-justified; safe to auto-act on;
  * **undecided** — the genuine choice set: a human or an LLM may pick ONLY from
    here, and cannot invent an option outside it;
  * **rejected** — invalid (failed its own re-derivation) or defeated.

This is the seam for automatic decision-making: the solver carves a *deterministic*
option space, and the stochastic part (the LLM) is confined to choosing within
`undecided`. The machine never proposes an option the space does not contain and
never picks a `rejected` one — the non-determinism is bounded by construction.

Two population mechanisms, matching the panel's discipline:
  * ``verify(candidate) -> (ok, reason)`` — a candidate that fails its OWN
    re-derivation is rejected outright (invalidity ≠ defeat);
  * ``defeat(a, b) -> 'a' | 'b' | None`` — pairwise ordering among VALID
    candidates; ``None`` = cannot separate = mutual attack = a genuine collision
    that stays undecided (escalates), never a fabricated winner.

Pure stdlib. No governance, no domain."""
from __future__ import annotations

from dataclasses import dataclass

IN, OUT, UNDEC = "in", "out", "undec"


def grounded_labels(nodes, attacks) -> dict:
    """Grounded (least-fixpoint) labelling of an abstract argumentation framework.

    ``nodes``: iterable of hashable ids. ``attacks``: iterable of
    ``(attacker, target)``. Returns ``{node: 'in' | 'out' | 'undec'}``. A node is
    IN iff every attacker is OUT (so a node whose only attacker is itself defeated
    is *reinstated*), OUT iff some attacker is IN, else UNDECIDED. The one grounded
    engine shared by the scenario resolver and the decision space."""
    nodes = list(nodes)
    atkset = set(attacks)
    attackers = {k: [a for (a, t) in atkset if t == k] for k in nodes}
    label = {k: UNDEC for k in nodes}
    changed = True
    while changed:
        changed = False
        for k in nodes:
            if label[k] != UNDEC:
                continue
            atk = attackers[k]
            if all(label[a] == OUT for a in atk):
                label[k] = IN; changed = True
            elif any(label[a] == IN for a in atk):
                label[k] = OUT; changed = True
    return label


@dataclass
class DecisionSpace:
    accepted: list        # grounded-justified — safe to auto-act on
    undecided: list       # the bounded choice set a human/LLM may pick within
    rejected: list        # [{id, reason}] — invalid or defeated
    attacks: list         # [(attacker, target)] — provenance of the space

    def choice_required(self) -> bool:
        """True when the space cannot be closed automatically — a human/LLM must
        pick from ``undecided`` (or the accepted set is the answer)."""
        return len(self.undecided) > 0

    def to_dict(self) -> dict:
        return {"accepted": sorted(self.accepted),
                "undecided": sorted(self.undecided),
                "rejected": sorted(self.rejected, key=lambda r: r["id"]),
                "attacks": sorted([list(a) for a in self.attacks]),
                "choice_required": self.choice_required()}


def _id(c):
    if isinstance(c, str):
        return c
    if isinstance(c, dict):
        return c["id"]
    return getattr(c, "id")


def decision_space(candidates, *, attacks=None, defeat=None, verify=None) -> DecisionSpace:
    """Carve the deterministic decision space over ``candidates``.

    See the module docstring for ``verify`` / ``defeat`` / ``attacks``. Returns a
    :class:`DecisionSpace`; an automatic decision-maker acts on ``accepted`` and,
    when ``choice_required()``, may select only from ``undecided``."""
    by_id = {_id(c): c for c in candidates}
    ids = list(by_id)
    rejected: list = []

    if verify is not None:
        valid = []
        for cid in ids:
            ok, reason = verify(by_id[cid])
            if ok:
                valid.append(cid)
            else:
                rejected.append({"id": cid, "reason": reason or "failed verification"})
    else:
        valid = list(ids)

    atk: set = set()
    for (a, b) in (attacks or []):
        if a in valid and b in valid:
            atk.add((a, b))
    if defeat is not None:
        for i in range(len(valid)):
            for j in range(i + 1, len(valid)):
                a, b = valid[i], valid[j]
                w = defeat(by_id[a], by_id[b])
                if w == "a":
                    atk.add((a, b))
                elif w == "b":
                    atk.add((b, a))
                else:                      # cannot separate -> mutual attack
                    atk.add((a, b)); atk.add((b, a))

    label = grounded_labels(valid, atk)
    accepted = [k for k in valid if label[k] == IN]
    undecided = [k for k in valid if label[k] == UNDEC]
    for k in valid:
        if label[k] == OUT:
            rejected.append({"id": k, "reason": "defeated by a stronger candidate"})
    return DecisionSpace(accepted, undecided, rejected, sorted(atk))
