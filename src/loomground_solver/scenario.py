# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Scenario layer (rung 4) — reasoning INSIDE a possible world.

A scenario is a world: a set of assumptions (norms held to apply), a graph of
dimensioned edges, and a frame (time / jurisdiction). Reasoning in a scenario is
two moves on the existing kernel:

  * **epistemic** — compose multi-hop inferences over the in-scope edges
    (:func:`reasoning.compose_paths`);
  * **normative** — for each act, resolve competing deontic conclusions with the
    injected rule-pack's defeaters (lex superior/specialis/posterior). A genuine
    collision the pack cannot separate does NOT auto-resolve — it ESCALATES
    (norm_contract NT-6), and the scenario answer for that act is *open*.

The *possible-worlds* payoff is :func:`compare`: run the same query across worlds
and see where the answer converges or diverges (an act obligatory in one world,
prohibited in another). Provenance is captured in full so a derivation can be
replayed and signed (:mod:`replay`). Pure: no governance, no domain, no I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import reasoning
from .decision import grounded_labels, IN, OUT, UNDEC
from .rulepacks import GENERIC_PACK, RulePack, contradicts


@dataclass(frozen=True)
class Norm:
    """A deontic claim in-scope in a world. rank/specificity/time feed the
    defeaters (lex superior / specialis / posterior); higher wins."""
    act: str
    deontic: str                 # 'obligatory' | 'permitted' | 'prohibited'
    source: str = ""
    rank: int = 0
    specificity: int = 0
    time: int = 0

    def to_dict(self) -> dict:
        return {"act": self.act, "deontic": self.deontic, "source": self.source,
                "rank": self.rank, "specificity": self.specificity, "time": self.time}


@dataclass
class Scenario:
    id: str
    norms: list = field(default_factory=list)     # list[Norm]
    edges: list = field(default_factory=list)     # list[pair dict] (dimensioned)
    time: str = ""
    jurisdiction: str = ""
    parent: str = ""                              # branching: derived from another world


@dataclass
class ActResolution:
    act: str
    status: str                  # 'determinate' | 'open'
    verdict: Optional[str]       # surviving deontic, or None
    survivors: list              # sources of surviving norms
    defeats: list                # [{loser, winner, rule}]
    collisions: list             # [(source_a, source_b)] genuine, unresolved


@dataclass
class ScenarioResult:
    scenario: str
    inferences: list             # list[reasoning.Inference] (epistemic closure)
    acts: dict                   # act -> ActResolution

    def resolution_for(self, act: str) -> Optional[ActResolution]:
        return self.acts.get(act)

    def trace(self) -> dict:
        """Canonical, order-stable provenance of the derivation (for replay)."""
        return {
            "scenario": self.scenario,
            "inferences": [
                {"subject": i.subject, "object": i.object,
                 "dimension": i.dimension.value if hasattr(i.dimension, "value") else str(i.dimension),
                 "confidence": round(float(i.confidence), 6), "hops": i.hops,
                 "path": [(e.get("subject"), e.get("predicate"), e.get("object"))
                          for e in i.path]}
                for i in self.inferences
            ],
            "acts": {
                a: {"status": r.status, "verdict": r.verdict,
                    "survivors": sorted(r.survivors),
                    "defeats": sorted([tuple(d.values()) for d in r.defeats]),
                    "collisions": sorted([tuple(sorted(c)) for c in r.collisions])}
                for a, r in sorted(self.acts.items())
            },
        }


def _resolve_act(act: str, norms: list, pack: RulePack) -> ActResolution:
    """Resolve competing norms on one act by the GROUNDED extension of the
    attack graph — reinstatement-sound, not naive pairwise defeat.

    Each contradiction the pack CAN separate is a directed attack (winner→loser);
    one it cannot separate is a MUTUAL attack (a genuine collision). A norm is IN
    iff every attacker is OUT (so a norm whose only attacker is itself defeated is
    *reinstated*); OUT iff some attacker is IN; else UNDECIDED. Undecided norms in
    a contradiction are a genuine, non-auto-resolvable collision → escalate."""
    n = range(len(norms))
    attacks: set = set()            # (attacker, target)
    rule_of: dict = {}              # (attacker, target) -> separating rule
    for i in n:
        for j in n:
            if i >= j:
                continue
            if not contradicts(norms[i].deontic, norms[j].deontic):
                continue
            w = pack.resolve(norms[i], norms[j])
            rule = pack.separating_rule(norms[i], norms[j])
            if w == "a":
                attacks.add((i, j)); rule_of[(i, j)] = rule
            elif w == "b":
                attacks.add((j, i)); rule_of[(j, i)] = rule
            else:                    # cannot separate -> mutual attack (genuine)
                attacks.add((i, j)); attacks.add((j, i))

    label = grounded_labels(list(n), attacks)   # the one shared grounded engine

    survivors = [k for k in n if label[k] == IN]
    defeats = [{"loser": norms[t].source, "winner": norms[a].source,
                "rule": rule_of[(a, t)]}
               for (a, t) in sorted(attacks)
               if label[a] == IN and label[t] == OUT and (a, t) in rule_of]
    collisions = [(norms[i].source, norms[j].source)
                  for i in n for j in n
                  if i < j and contradicts(norms[i].deontic, norms[j].deontic)
                  and label[i] == UNDEC and label[j] == UNDEC]
    if collisions:
        return ActResolution(act, "open", None,
                             [norms[k].source for k in survivors], defeats, collisions)
    verdicts = {norms[k].deontic for k in survivors}
    verdict = ("obligatory" if "obligatory" in verdicts
               else "prohibited" if "prohibited" in verdicts
               else "permitted" if "permitted" in verdicts else None)
    return ActResolution(act, "determinate" if verdict else "open", verdict,
                         [norms[k].source for k in survivors], defeats, [])


def derive(scenario: Scenario, *, pack: RulePack = GENERIC_PACK) -> ScenarioResult:
    """Reason inside one world: epistemic closure over the edges + defeasible
    normative resolution per act under ``pack``."""
    edges = reasoning.extract_edges(scenario.edges)
    infs = reasoning.compose_paths(edges)
    by_act: dict = {}
    for nrm in scenario.norms:
        by_act.setdefault(nrm.act, []).append(nrm)
    acts = {act: _resolve_act(act, ns, pack) for act, ns in by_act.items()}
    return ScenarioResult(scenario.id, infs, acts)


def compare(scenarios: list, act: str, *, pack: RulePack = GENERIC_PACK) -> dict:
    """Possible-worlds view: ``scenario_id -> (status, verdict)`` for ``act``
    across worlds. Divergence is the point — the same act can be obligatory in one
    world and prohibited in another."""
    out = {}
    for s in scenarios:
        r = derive(s, pack=pack).resolution_for(act)
        out[s.id] = (r.status, r.verdict) if r else ("absent", None)
    return out


def to_case(result: ScenarioResult, act: str, *, profile: str = "generic",
            document: str = "") -> dict:
    """Project a scenario's answer for ``act`` into a reasoning-contract case
    (feeds :func:`contract.check_case`). Determinate -> a determinate answer;
    an unresolved collision -> a residual surface with no recorded choice (open),
    so the judgment floor makes a human originate the resolution."""
    r = result.resolution_for(act)
    if r is None:
        raise KeyError(f"act {act!r} not in scenario {result.scenario!r}")
    grounds = [{"pinpoint": s, "receipted": True} for s in r.survivors] or \
              [{"pinpoint": "(no surviving norm)", "receipted": True}]
    chain = [{"step": "defeater",
              "text": f"{d['winner']} defeats {d['loser']}",
              "warrant": d["rule"] or "unspecified"} for d in r.defeats]
    if not chain:
        chain = [{"step": "rule", "text": f"norms applying to {act}",
                  "warrant": "applicability"}]
    if r.status == "determinate":
        resolution = {"type": "determinate", "answer": f"{act}: {r.verdict}"}
    else:
        opts = [{"id": src, "conclusion": f"{act}: (contested)"} for pair in r.collisions
                for src in pair]
        # dedupe, keep >=2 so it reads as a real choice
        seen, options = set(), []
        for o in opts:
            if o["id"] not in seen:
                seen.add(o["id"]); options.append(o)
        while len(options) < 2:
            options.append({"id": f"open-{len(options)}", "conclusion": "unresolved"})
        resolution = {"type": "residual", "surface": {"options": options}}  # no choice => open
    return {
        "problem": {"text": f"What is the deontic status of {act}?", "document": document},
        "facts": [], "grounds": grounds, "chain": chain, "gaps": [], "coverage": 1.0,
        "resolution": resolution, "profile": profile,
    }
