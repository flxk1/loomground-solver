<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Roadmap slice — reasoning work for agentic oversight

Status: **draft, not committed scope.** Non-normative.

A set of open problems in agentic oversight lands mostly on this kernel, because
most of them are reasoning problems wearing governance clothes. This slice
records what the kernel already answers, what it does not, and what would have to
be true to claim otherwise.

> **Where this work now lives.** Six of the items below — the oversight brief,
> falsifiability ranking, conjunctive collapse, mandate divergence, the escalation
> ceiling and proxy substitution — were built in this repository and have since
> been **moved out**, one narrow repository each: `loomground-brief`,
> `loomground-falsifiability`, `loomground-collapse`, `loomground-mandate`,
> `loomground-escalation`, `loomground-proxy`. They were never released from here.
>
> The reason is the frame below, applied one level up than it was written. The
> gate forbids importing governance or a domain; it does not by itself stop
> *subject vocabulary* accumulating in a kernel whose whole claim is that it holds
> none. Agentic oversight is a subject area. Those six are its vocabulary, and they
> were written here because that is where their imports were nearest — not because
> the reasoning substrate needs them. Each now sits **above** this package,
> depending on the shared verdict, the OPEN-dominant fold and the injected ports,
> and reaching into no internals.
>
> One thing stayed: `epistemic_status.root_causes` (S2). Ordering a premise graph
> by what presupposes what is reasoning, not oversight, so it belongs here and the
> brief consumes it from here.
>
> The sections below are kept as written. What each item is and why it takes the
> shape it does is the durable part; which repository holds it is not.

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

*Landed as `divergence`*: a trajectory compared against a `Mandate`, reporting
`ungrounded`, `out-of-mandate`, `defeats-purpose` and `unserved`. Whether a step
serves or defeats a purpose arrives already judged, and purposes stay opaque
identifiers — a purpose must not become a kernel concept.

**Corrected after first landing.** The first version took the mandate and the
steps as flat local types with a `ref` that was an unchecked string, which made
the comparison only as good as the caller's assertion — the failure this whole
layer exists to refuse, reproduced inside the detector meant to catch it. The
mandate and the trajectory live one layer down, in the knowledge engine that
anchors claims to spans and refuses an ungrounded step; keeping the layers
*separate* had been achieved by keeping them **disconnected**.

Both terms now carry an `EvidenceRef` and `detect` requires an `EvidenceProvider`
it actually calls `verify` on — through the injected port, so the grounding is
real without the substrate being imported. There is no permissive default and no
in-package no-op provider: a caller who wants findings without verification must
write the provider that returns `True`, and thereby say so. An unverifiable
mandate stops the comparison outright, being the second term of every comparison
made here; an unverifiable step costs only itself, and is dropped from the record
of what the run served so an unresolvable step cannot discharge a declared
purpose.

The claim that **the proxy-optimisation case is the same shape turned out to be
wrong**, and it is worth recording why. A divergence needs someone to hand in the
judgement that a step defeated a purpose, and the whole difficulty of proxy
optimisation is that nobody has that judgement: the metric improved, and what it
stands for was never measured. The missing term is not the purpose but the
**substitution** — the declaration that this measurement stands for that goal —
and once it is written down the failure is checkable from two readings.

Landed as `proxy`, alongside rather than inside `divergence`: `gamed` (metric up,
goal down), `unchecked` (nobody measured the goal, so the reading is no evidence
about it, which is the common case and must never read as success), `misleading`
(the instrument rather than the run is in doubt), `tracking`. Substitutions
chain, support along a chain is weakest-link through the existing fold, and a
chain that cycles is refused rather than truncated — a substitution grounding in
nothing is the absence of a justification, not a weak one.

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

*Landed as `escalation`, in a different shape than sketched here.* Composing
`proportionality`, `epistemic_status` and `burden` into an autonomy level would
have meant shipping the mapping from a named factor to a rung, and that mapping
is a claim about a deployment rather than about reasoning — policy smuggled into
the mechanism. What the kernel contributes instead is the **fold**: each factor
imposes a ceiling on an ordered ladder and the actor gets the lowest one, which
is monotone (nothing compensates for anything), attributable (the capping factor
is named, and a name is actionable where a magnitude is not), and fail-closed (an
unassessed factor caps at the floor rather than dropping out of the minimum).
Which factor caps where stays the caller's.

The escalation discipline the kernel applies everywhere else holds: an
incompletely assessed tuple maps to `OPEN` rather than passing, and the calculus
only ever lowers — restoring autonomy requires a reference to the authorisation
for restoring it, because an escalation follows from the state of the world while
a de-escalation is an act someone is answerable for.

**Corrected after first landing.** The first version applied that reasoning to
the factor→rung *table* and then shipped the rungs themselves — a fixed
`SUSPENDED < PROPOSE < CONFIRM < NOTIFY < ACT` enum, in the kernel. The
governance language already owns this ladder and already publishes it as
remappable data, saying so in as many words: *policy supplies the levels, their
meanings, and their order; the language owns only the comparison rule.* A second
ladder here was a divergent copy in the layer that holds no deployments, and a
host would have had to map one onto the other — which is where two ladders drift.

The ladder is now a caller-supplied `Ladder` of ordered level names, following
the pattern this kernel already uses for anything subject-bearing (`PROFILES`,
`PACKS`, `register_filter`, `register_method`). A host reads its levels from
wherever it keeps its policy. `ceiling()` is a minimum over a total order, so it
never needed particular rungs; a test greps the module to prove none ship, and a
level off the ladder is refused rather than coerced to the floor — a wiring
mistake must not become a conservative-looking policy.

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
