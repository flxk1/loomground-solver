<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Roadmap slice — reasoning work for agentic oversight

Status: **draft, not committed scope.** Non-normative.

A set of open problems in agentic oversight lands mostly on this kernel, because
most of them are reasoning problems wearing governance clothes. This slice
records what the kernel already answers, what it does not, and what would have to
be true to claim otherwise.

The dependency-inversion gate is the frame for all of it: **nothing proposed here
may import governance or a domain module, or carry a domain literal in executable
code.** Everything below arrives through injected ports or is domain-neutral by
construction. A step that fails `tests/test_dependency_inversion.py` is wrong
regardless of its merits.

---

## Two claims the kernel can already almost make

### The oversight-information claim

Human review does not scale with agent autonomy: reading every intermediate step
defeats the purpose of delegation, and sampling steps leaves blind spots. The
question — *what is the minimum information a supervisor needs to exercise
meaningful oversight?* — is normally treated as open.

Empirically, shipping the action trace does not answer it. Traces raise a
reviewer's confidence without improving their detection of errors, which makes
trace-shipping worse than useless: it manufactures the feeling of oversight
without the fact.

The kernel already computes a better-shaped object, in four places that were
built for other reasons:

| Existing | What it holds |
|---|---|
| `fingerprint` negative space | unfired defeaters, untriggered exceptions, gaps |
| `epistemic_status` | premises that are contested, presupposed, or unknown |
| `decision` | the `undecided` set — the genuine choice set, bounded |
| `gap_fork` | resolutions the contract refused to let stand |

The union of those is where errors actually live, and — this is the load-bearing
property — **its size is a function of what the reasoning could not settle, not
of how many actions were taken.** A run of a thousand steps that settles cleanly
has a small brief; a run of ten that does not has a large one. That is the
scalability claim, and it is measurable rather than rhetorical.

*Candidate shape.* `oversight_brief()` — a bounded selection over those four
sources plus mandate divergence (below), with each entry carrying its own
derivation. Not a new engine; a selection over what the fold already produces.

### The regress claim

If an overseeing agent is needed because the supervised agent is too capable to
review directly, the obvious objection is regress: who oversees the overseer?

This kernel supports a specific answer — *nobody does, directly.* The overseer
emits a **replayable derivation**, and a model-free checker re-derives it. The
deterministic floor is already here: the kernel is standard-library-only apart
from a data-only package, `replay` makes a run re-derivable, and the conformance
vectors fix the contract. What a human then supervises is a small fixed
model-free contract, and that burden does not grow with the capability of what is
being overseen.

The claim is falsifiable and currently unproven. It holds only if I2 below holds:
an oversight decision must be re-derivable **without the model that produced
it**. Until that is demonstrated, the regress argument is a design intent, not a
result.

---

## Gaps

### S1 · No mandate, so no divergence

The characteristic agentic failure is not an implausible action. It is a
sequence of locally reasonable actions that is globally wrong — a
misunderstood objective, an optimised proxy, or literal compliance that defeats
the purpose.

The kernel can compose a path, subsume a case under a norm, and detect a
contradiction. It cannot detect divergence, because divergence is a relation
between a trajectory and an **authorising purpose**, and no such term is
available to it. Nothing here needs inventing: the purpose arrives through the
existing port discipline, from the graph or the host, as an ordinary premise.

*Candidate shape.* A divergence check over `compose_paths`, `subsumption` and
`cross_subsumption`: the trajectory either fails to subsume under the purpose, or
subsumes literally while a defeater fires. `interpret.audit` already catches the
self-contradictory or unwarranted move; the proxy-optimisation case is the same
shape.

### S2 · Root cause is not surfaced ahead of its consequences

An early assumption that propagates through fifty later actions is the failure
mode that makes review hopeless — every one of the fifty looks defensible, and
the defect is upstream of all of them.

The kernel already models this exactly: it is a `PRESUPPOSED` premise under the
OPEN-dominant strict-AND fold in `issue_aggregation`. What it does not do is
report the **root** rather than the descendants. Surfacing the presupposition
instead of its fifty consequences is the single largest compression available to
oversight — one line replaces fifty — and it needs no new inference, only an
ordering over what the fold already knows.

### S3 · No escalation calculus

An autonomy level that varies with risk, uncertainty, reversibility, context and
competence is a composition problem, and the parts are present:
`proportionality` weighs, `epistemic_status` supplies settledness, `burden`
carries who must show what, `decision` bounds the option space.

*Candidate shape.* Compose the tuple and return a **declaration with a replayable
derivation** — never a verdict. The kernel does not decide autonomy; it computes
a defensible input to a host that does. An underdetermined tuple escalates,
following the discipline the kernel already applies everywhere else: a collision
it cannot separate stays undecided rather than becoming a fabricated winner.

### S4 · Oversight signals are untyped

Plans, tool calls, outcomes, internal reasoning and independent verification are
all treated as evidence of the same kind. They are not, and the ordering that
matters is **how each can be falsified**:

```
replayable derivation  >  span-grounded claim  >  independently verified
outcome  >  observed tool call  >  declared plan  >  self-reported reasoning
```

Self-reported reasoning sits last on principle, not on suspicion: it is an
unfalsifiable claim about a private mechanism. It may inform a decision; it may
never be the sole basis for one.

*Candidate shape.* A falsifiability rank on evidence, folded through the existing
verdict vocabulary so that a conclusion resting solely on the weakest rank
escalates rather than passes.

### S5 · The control topology is unmodelled

`topology` already validates a **derived solver** structure as a typed DAG, with
governance riding on node kind rather than flow position, and a deterministic
topological order. That is the right primitive for a different graph the family
does not yet build: the topology of principals, agents, monitors, checkpoints and
escalation paths — oversight as a network rather than as a node.

The interesting checks are structural and cheap once the graph exists: is every
agent on a path to a checkpoint; is any monitor downstream of what it monitors;
does removing one node disconnect every escalation path.

### S6 · The conjunction rule for control constituents already exists

Oversight decomposed into observability, intervenability, comprehensibility,
authority and timeliness is a conjunction where any single term at zero collapses
the whole. That is the OPEN-dominant strict-AND fold, exactly. It should be
**reused, not rebuilt** — a second collapse rule beside `issue_aggregation` would
be a fork of the honesty verdict, which the epistemic-status layer was careful
not to create.

---

## Sequencing

| Step | Gap | Notes |
|---|---|---|
| 1 | S2 | Cheapest and highest leverage; ordering over an existing fold |
| 2 | S1 | Needs the purpose term through a port |
| 3 | S4 | Rank, then fold |
| 4 | S3 | Composition over `proportionality` / `epistemic_status` |
| 5 | S6, then the brief | Reuse the fold; assemble `oversight_brief()` |
| 6 | S5 | New graph, existing validator shape |
| 7 | I2 — replay without the producing model | Gates the regress claim |

## Gates

- `tests/test_dependency_inversion.py` — no governance import, no domain module,
  no domain literal. **This passing is the definition of universal**, and it
  applies to every step above without exception.
- `tests/test_api_parity.py` — the public surface stays re-exported.
- `python3 -m pytest` green.
- For the oversight-information claim specifically: brief size measured across
  runs of 10, 100 and 1000 actions on one purpose. **A brief that grows with
  action count has falsified the claim** and should be reported as such rather
  than tuned until it does not.
- For the regress claim: an oversight decision re-derived without the model that
  produced it, or the claim is withdrawn.

## What stays out

No governance vocabulary, no domain pack, no persistence, no enforcement, no
escalation *action*. The kernel computes and justifies; a host decides and acts.
The purpose term, the trajectory and the competence estimate all arrive through
`ports` — none of them becomes a kernel concept.
