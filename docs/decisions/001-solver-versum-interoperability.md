# ADR 001: Solver–Versum interoperability ownership and failure semantics

- Status: Accepted
- Date: 2026-07-21
- Decision owner: product owner
- Scope: Solver reference reasoning adapter and its Versum seam

## Context

Solver and Versum independently implement the `reasoning.interop/1.0` wire
records. Their first implementations were byte-identical copies, while Versum
emitted `loomground.versum.claim-axes/v1` and Solver's neutral compiler accepted
only `reasoning.edges/v1`. The neutral service consequently returned
`complete` while rejecting a candidate because it did not understand the
candidate's structural schema. Versum also initially emitted no minted graph
snapshot and exposed no store-backed evidence facade.

The products must remain standalone. Solver must not import Versum, Versum must
not import Solver, cells are only a possible future topology, and no shared
`loomground-interop` runtime package will be created.

## Decision

### Tool-owned interoperability

The Loomground language supplies shared semantic vocabulary only. It does not
own operational interoperability envelopes or a companion interop standard.

Every tool owns its adapter, operational contract, schemas, compatibility
rules, limits and conformance fixtures. A tool integrating with another tool
implements the required translation at its own boundary and proves it through
bilateral and cross-product tests. Shared test vectors may be copied as
versioned fixtures for differential verification, but they have no separate
governing package or standard and contain no runtime adapter code.

### Neutral default and explicit composition

Solver's neutral `default_service()` accepts only installed canonical
structural schemas. It does not silently install product-specific adapters.

A host that composes Solver with Versum explicitly installs
`ClaimAxesDecoder`. The decoder validates and losslessly preserves the five
recognized claim axes under hard bounds. The 0.1.0 profile is deliberately inert:
it invents no logical edges, attacks or deontic consequences. Later semantic
profiles require separately versioned, closed mappings.

### Request-level escalation

Unsupported request semantics are not candidate verdicts. Before evidence or
candidate adjudication, Solver preflights:

- whether every declared structural schema has an installed compiler; and
- when a snapshot-bound provider is used, whether every evidence reference
  names that provider's snapshot.

A gap returns a signed `ReasoningResult` with:

- `status = "escalate"`;
- empty `accepted`, `undecided` and `rejected` partitions; and
- structured `trace.errors[]` diagnostics.

Malformed evidence or malformed data under a supported schema may still reject
the affected candidate. Unsupported semantics escalate the request because the
service cannot make a substantive judgment.

### Identity and authority

`canonical_urn` identifies the grounded source or span. Extracted claims,
compiled rules, attacks and conclusions mint their own identities and retain
their grounding chain. Solver never mints source identities.

Content addressing permits computation reuse only when all semantic inputs
match. Every consumer verifies integrity and authorizes validity locally;
authority never travels with a digest or signature.

### Product boundary

Versum describes and selects. It may emit attested contextual assignments,
candidate contradiction relations and, after their own gates, deontic or
conditional compositions. It does not decide effective force, normative
priority or defeat.

Solver decodes installed schemas and performs adjudicative reasoning. Polarity
is never automatically translated into attack. RVND or another host owns
authorization, assurance and normative priority.

## Consequences

- Solver and Versum keep separate adapter contracts and implementations;
  bilateral and differential integration tests detect drift.
- The neutral default fails closed while an explicitly composed service accepts
  conforming Versum claim axes.
- The 0.1.0 profile proves bounded, classified transport, not governance semantics.
- Versum snapshot and evidence work can evolve independently behind the agreed
  ports.
- The system-scale architecture remains north-star guidance implemented through
  each tool's adapter responsibilities, without becoming another package,
  standard or service.

## Rejected alternatives

### Shared interoperability package or companion standard

Rejected by owner ruling. The language supplies semantics; each tool owns all
operational interoperability at its adapter boundary.

### Install the Versum compiler in Solver's neutral default

Rejected because it would make a product-specific schema implicit in the
standalone kernel.

### Down-map claim axes silently to generic edges

Rejected because an undefined mapping could discard or invent semantics. Any
operative mapping requires a versioned semantic profile.

### Reject candidates when their schema is unsupported

Rejected because inability to understand a request is not evidence against the
candidate.

## Verification

- `tests/test_wire_claim_axes.py` proves neutral escalation and explicit
  composition.
- `tests/test_universal_handler.py` proves structured schema and snapshot
  escalation while retaining candidate rejection for ordinary evidence
  failures.
- Versum's live-store integration proves a minted snapshot and store-backed
  evidence provider can drive the composed Solver handler.
