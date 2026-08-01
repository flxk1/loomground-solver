# Universal graph–solver interoperability

Solver implements the vendor-neutral `reasoning.interop` 1.0 wire contract in
`loomground_solver.interop`. The contract is data-only and JSON-safe: a graph or candidate
producer does not import Solver, and Solver does not import that producer.

The protocol separates four concerns:

1. A `ProtocolManifest` advertises roles, schema identifiers, and optional capabilities.
2. `EvidenceRef` identifies evidence using an opaque source identifier, optional item/span,
   digest, graph version, and implementation-specific locator/extensions.
3. `Candidate` carries an untrusted claim plus its grounding and structural evidence. Ranking
   metadata is informational and never proof weight.
4. `ReasoningRequest` and `ReasoningResult` form the transport-neutral request/response pair.

Solver-specific behavior is expressed through `EvidenceProvider`, `CandidateProvider`, and
`ReasoningService` ports. Implementations may communicate in-process, via JSON files, queues,
or HTTP. Unsupported required capabilities must be rejected or escalated, never guessed.

Versum is one possible graph implementation. No `versum` import is permitted inside
`loomground_solver/`; dependency-inversion tests enforce that boundary.

## Reference implementation

`default_service()` supplies a complete standalone verifier. It validates the
envelope, resolves versioned Solver profiles, verifies inline evidence and
SHA-256 digests, compiles the neutral `reasoning.edges/v1` structure, computes a
bounded decision space, and returns a deterministic signed trace.

Inline evidence is provided in the request extensions:

```json
{
  "extensions": {
    "inline_evidence": [
      {"source_id": "doc-1", "item_id": "p1", "content": "Exact claim"}
    ]
  }
}
```

For external stores, construct `UniversalHandler(evidence_provider=...)`. For a
graph-specific structural schema, also inject one or more `StructuralCompiler`
implementations. The neutral protocol remains unchanged.

## Request-level escalation

The handler preflights contract semantics before candidate adjudication. If a
request declares a structural schema for which no compiler is installed, or if
evidence references do not match an injected snapshot-bound provider, the
result is a signed request-level escalation:

```json
{
  "status": "escalate",
  "accepted": [],
  "undecided": [],
  "rejected": {},
  "trace": {
    "errors": [{
      "code": "unsupported_structural_schema",
      "scope": "request",
      "schema": "vendor.private/v9",
      "candidate_ids": ["candidate-1"]
    }]
  }
}
```

Snapshot gaps carry distinct codes: `evidence_snapshot_missing` when a
reference names no graph snapshot at all, `evidence_snapshot_mismatch` when a
well-formed snapshot id does not match the provider's. Both escalate; the
codes let the caller distinguish an incomplete request from a stale one.

An unsupported contract is not evidence against a candidate. Malformed
evidence or malformed data under a supported schema may still reject the
affected candidate. Product-specific compilers remain explicitly installed;
the neutral default does not acquire their semantics implicitly.

## Immutable context extension

An optional world-model provider may attach context identity under
`extensions.context_snapshot`:

```json
{
  "extensions": {
    "context_snapshot": {
      "snapshot_id": "context:42",
      "digest": "sha256:...",
      "created_at": "2026-07-19T00:00:00Z",
      "findings": [{"kind": "context-freshness", "freshness": "stale"}]
    }
  }
}
```

Solver validates and copies only this identity and its explicit findings into
the signed trace. Beliefs and evidence contents remain with the provider. The
extension does not alter inference or widen `accepted`; changing it changes the
signature so the exact context remains replay-identifiable.

## Loomground language route

A producer can submit a Loomground program without candidate envelopes. This is
the standard request shape:

```json
{
  "protocol": "reasoning.interop",
  "protocol_version": "1.0",
  "kind": "reasoning_request",
  "request_id": "lg-1",
  "problem": {
    "language": "loomground",
    "language_version": "0.8.2",
    "source": "actor bot ...",
    "transport": {"activations": []}
  },
  "candidates": [],
  "solver_profile": "loomground@0.8.2",
  "required_capabilities": ["loomground-governance", "signed-replay"]
}
```

The result maps released token IDs to `accepted`, `human`/`reserved` token IDs
to `undecided`, and `refused`/`prohibited` token IDs to `rejected`. The complete
canonical observation, gate evaluation and ordered Loomground log remain in the
signed trace.

Loomground is a Solver language route, not a graph extension. Graphs remain
language-neutral evidence and structural providers and need no Loomground-aware
schema, storage model or projection.
