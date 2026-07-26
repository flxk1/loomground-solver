# ADR 002: Claim-axes vocabulary lives in the language repo as a companion

- Status: Accepted
- Date: 2026-07-22
- Decision owner: product owner
- Supersedes: the "no companion interop standard" clause of ADR 001 for the
  *semantic vocabulary only*; every other ADR 001 decision stands.

## Context

ADR 001 fixed tool-owned operational interoperability and left the claim-axes
vocabulary's canonical home open. Placing the vocabulary in the language
repository fits its existing companion/profile mechanism — spec + schemas +
fixtures beside the language, not in it — rather than duplicating it inside
each consuming tool.

## Decision

The companion profiles live in the language repo:

- The canonical claim-axes vocabulary, wire-record schema, inert 0.1.0 profile
  (closed sets; polarity is permanently non-attack), and shared conformance
  vectors live at `loomground-governance/standard/companions/claim-axes/`.
- Operational interoperability stays exactly where ADR 001 put it: each tool
  owns its adapter, operational contract, limits, and conformance fixtures at
  its own boundary. The companion carries no runtime adapter code.
- The wire identifier `loomground.versum.claim-axes/v1` is frozen; the
  `versum` segment records origin, not ownership.
- Tools vendor the vectors as versioned copies (this repo:
  `tests/fixtures/claim_axes_vectors/`) and prove conformance differentially —
  the Solver decoder and the Versum producer are the companion's two
  independent implementations.
- New axis semantics arrive as new companion profile versions with their own
  closed sets, never by widening 0.1.0's.
