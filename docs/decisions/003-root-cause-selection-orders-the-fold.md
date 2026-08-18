<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# ADR 003: Root-cause selection orders the fold; it does not decide

- Status: Accepted
- Date: 2026-08-17
- Decision owner: product owner
- Scope: `epistemic_status.root_causes` / `RootCauseReport`

## Context

The characteristic failure of a long derivation is not an implausible step. It
is an early assumption that propagates: every later step is individually
defensible, each inherits the assumption's openness, and the defect sits
upstream of all of them.

The layer already models this. A `PRESUPPOSED` premise is unsettled, the
OPEN-dominant fold in `issue_aggregation` makes the whole set OPEN, and
`IssueAggregate.issues` lists every sub-issue that contributed. What it does not
do is distinguish the one premise that is open *on its own status* from the
fifty that are open only because they rest on it. A reader is handed fifty
items, all true, of which one is the cause.

## Decision

### 1. Order, never decide

`root_causes` returns `overall` from `propagate_premises` — the same fold, not a
second opinion. Nothing here re-derives a verdict, mints a status, or changes
what is open. It partitions names that the existing fold already classified. A
test asserts `root_causes(p).overall == propagate_premises(p).overall` across
open, closed, and empty sets, and another asserts the partition is total and
disjoint.

### 2. A root is a premise unsettled on its own status

Settling something else cannot settle a premise that is itself `PRESUPPOSED`,
`CONTESTED` or `UNKNOWN`. So every independently-unsettled premise is a root,
including one that also depends on another root — it is not *derived* from it in
the sense that matters. Only a premise with a **settled** status that
transitively rests on a root is `derived`.

This is what produces the useful compression: fifty `INFERRED` steps resting on
one `PRESUPPOSED` assumption yield `(1, 51)`, and the ratio does not grow with
chain length.

### 3. Dependencies are declared, not inferred

`StatusedPremise.depends_on` is tagged by the same party that tags `status`,
consistent with this layer's existing honesty note that status is asserted, not
read off the fact. It defaults to empty, so every existing caller is unaffected,
and the folds never read it — only `root_causes` does.

### 4. Both bad shapes are surfaced, not smoothed

A dependency naming no premise in the set is reported as `dangling`: the set is
under-described, and a reader must know that before trusting the partition. A
premise on a dependency cycle is reported as `cyclic` and lands in neither
`roots` nor `derived`, because choosing a root inside a cycle would be a
fabricated answer — the same escalate-don't-guess rule the rest of the kernel
applies.

### 5. Iterative traversal

Cycle detection and inheritance both use explicit stacks with visited sets. A
3000-step chain is a realistic agent trajectory and must not exhaust the
interpreter stack; a test pins that depth.

## Consequences

**Gained.** The oversight-facing claim becomes measurable: the causal set is
bounded by what was actually unsettled, not by how long the derivation ran. That
is the property a bounded oversight brief needs, and it is now a test rather
than an aspiration.

**Given up.** Compression depends entirely on callers declaring `depends_on`. A
set that declares none reports every unsettled premise as a root, which is
correct but uncompressed. This layer will not infer dependencies from names,
ordering, or timing — that would be guessing at structure.

**Boundary.** `root_causes` says which premises are causes *within the set it is
given*. It does not reach outside it, and a root here may itself be a
consequence of something never tagged. Nothing in the return should be read as
"this is the origin of the error" — only as "this is where the set stops
explaining itself."
