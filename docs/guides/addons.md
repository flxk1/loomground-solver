# Optional add-ons

Solver's deterministic kernel does not import or activate add-ons. A host may
load optional context providers and run observers by explicitly calling
`loomground_solver.addons.load_addons(config)`.

```toml
[solver.addons.world_model]
mode = "recommend" # off | recommend | required
provider = "my_product.solver_addons:create_context_provider"

[solver.addons.world_model.options]
source = "configured-by-host"

[solver.addons.metacognition]
mode = "manual" # off | manual | scheduled
observers = ["my_product.solver_addons:create_gap_observer"]

[solver.addons.metacognition.options]
proposal_store = "./solver-proposals"
```

The loader accepts the parsed mapping; it does not choose a configuration-file
format or read files itself:

```python
import tomllib
from loomground_solver.addons import load_addons
from my_product.solver_addons import create_context_provider, create_gap_observer

with open("solver.toml", "rb") as handle:
    config = tomllib.load(handle)

runtime = load_addons(config, authorized_factories={
    "my_product.solver_addons:create_context_provider": create_context_provider,
    "my_product.solver_addons:create_gap_observer": create_gap_observer,
})

snapshot = runtime.context_provider.snapshot(request)
```

In `recommend` or `manual` mode, advice does not load code. After applying its
own authorization policy, the host selects an add-on explicitly:

```python
runtime = load_addons(
    config,
    selected=("world_model",),
    authorized_factories={
        "my_product.solver_addons:create_context_provider": create_context_provider,
    },
)
```

Configuration never imports code. The host imports reviewed implementations and
passes an explicit reference-to-callable registry; an active reference absent
from that registry fails closed.

`required` loads the configured world-model provider and fails closed when it
is missing. `scheduled` loads configured observers when the host starts its
scheduled analysis job. `off` always wins over other fields.

The provider factory receives its `options` mapping and must return an object
implementing `ContextProvider`. Observer factories also receive their options.
Absent or disabled configuration returns an empty `AddonRuntime` and preserves
pure Solver behavior.

## Deterministic advisor skill

`loomground_solver.addons.advise(payload)` is a pure, side-effect-free skill
surface. It scores a world-model recommendation by counting declared request
signals: time sensitivity, current-state dependence, evidence references,
multiple sources, possible conflicts and freshness requirements. The default
recommendation threshold is two signals.

Metacognition is eligible only when its batch contains the configured minimum
number of records marked verified and those records occupy at most one scope.
`manual` mode remains eligible but is never automatically recommended;
`scheduled` mode may be recommended. Actual observers still cryptographically
verify records when converting them to observations.

The result lists scores, thresholds, reasons, required/missing inputs, benefits
and risks and always contains `activation_performed: false`. Its manifest is
available from `skill_manifest()` as `solver.addon-advisor`.

## Evaluation and governed lifecycle

Metacognitive observations use the stable `SignedRunRecord` and a host-supplied
`RunVerifier`. A proposal evaluation must contain training, regression,
adversarial and holdout cases. Every case in every partition must pass before
the report becomes promotion-eligible.

`authorize()` records a non-empty external authorization reference;
`promote()` then creates a content-digested `ArtifactVersion`. Neither function
deploys an artifact. `rollback()` creates an authorization- and evidence-bearing
rollback record, and `JsonlVersionRegistry` can preserve version/rollback
evidence by scope. Applying a promotion or rollback remains the host's job.

## World model boundary

The add-on provides immutable `Belief` and `ContextSnapshot` values,
deterministic Bayesian-style evidence updates, explicit freshness assessment,
and content-addressed snapshots. `sign_contextual` binds the exact snapshot to
a replay signature without changing Solver's inference or resolution rules.

The host owns evidence acquisition and persistence. Versum or another graph may
supply evidence through an adapter, but Solver never imports that product and
does not maintain a second knowledge graph.

## Metacognition boundary

Metacognition projects immutable signed run records into `Observation` values.
The projection requires a host-supplied replay/signature verifier and rejects a
record when verification fails.
It groups recurring structural gaps deterministically and emits draft
`ImprovementProposal` records. `JsonlProposalStore` is optional and isolated by
scope. It refuses operational promotion states.

Promotion, policy mutation, deployment and authorization remain external. No
add-on silently changes code, rule packs, thresholds, examples or policy.

## Adaptation provenance

The bounded belief-update, freshness and recurring-gap mechanics were adapted
from an external prior implementation. What carried over: bounded belief
updates, staleness detection, and deterministic grouping of recurring
structural gaps into draft improvement proposals. What was deliberately left
out: multi-agent orchestration, shared blackboards, domain-specific legal
constants, entity resolution, temporal/counterfactual reasoning, knowledge-
graph writes, HTTP routes and automatic approval.
