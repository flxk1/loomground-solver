# loomground-solver

A universal reasoning and decision kernel, packaged standalone so that both a
knowledge graph (the 5D+nD Versum) and a governance layer (host) can **import it
without owning it**. Governance and corpus arrive only through injected ports, so
the same kernel runs unchanged as the graph's derived-truth layer, as a standalone
path-solver that writes nothing, and as host's clamped verdict instance.

The runtime is standard-library-only apart from the data-only
`loomground-governance` package, consumed from
[`flxk1/loomground-governance`](https://github.com/flxk1/loomground-governance) as
a pinned, published version (`>=0.8,<0.9`) — never an unpinned branch, so a
release can always be reinstalled identically.

It can pair with any knowledge graph through the vendor-neutral
[`reasoning.interop` 1.0 contract](docs/contracts/reasoning-interop.md), while remaining fully standalone. Versum is
one conforming graph, not a core dependency.

Loomground language support and its explicit version policy are documented in
[Loomground compatibility policy](docs/contracts/loomground-compatibility.md).
Cross-repository release order and automated version administration are defined
in the [release and versioning guide](docs/guides/releasing.md).

Solver exposes a packaged universal-adapter boundary. Loomground is
the built-in reference adapter: it projects canonical observations into ordinary
Federation-5D reasoning pairs and typed, versioned nD coordinates without coupling
Solver to Versum. Additional systems can implement `SystemAdapter` and register through
`AdapterRegistry`. The same package contains the Versum corpus adapter and opt-in
fingerprint adapters under `loomground_solver.adapters`; there is no separate
`integrations/` compatibility layer.

## What it does

The kernel is a **verifier + structured world model**, not a retriever. A generator
(any reasoning model) proposes; the solver disposes — with a name and a proof.

- 5D edge model + composition algebra (structural / causal / intentional / temporal
  / relational).
- Path composition over the dimensioned graph — the epistemic solver.
- A justified-answer contract (PASS / VIOLATION / ESCALATE) with profiles.
- Subsumption and end-to-end rule reasoning (Tatbestand → Rechtsfolge + exception).
- Scenario / possible-worlds resolution with grounded (reinstatement-sound)
  defeasibility and rule-packs.
- A deterministic decision space: `accepted` / `undecided` / `rejected`, where an
  automatic decision-maker acts on `accepted`, is confined to `undecided`, and
  cannot touch `rejected`.
- A pluggable-filter **fingerprint** (an open nD family): the normal-mode edges
  (`logical_form`), the attack topology, the negative space (unfired defeaters /
  untriggered exceptions / gaps), argument types, statistics, and the
  cross-domain `contradiction` invariant — register your own in one line.
- **Federation** — reasoning in fingerprint space: narrow an unknown problem's
  solution by inference over a body of problem→solution fingerprint pairs, and
  escalate (never guess) the coordinates the federation does not pin down.
- An open registry of 19 reasoning methods across logic, philosophy, methodology,
  rationalist decision theory, mathematics, and data science (`register_method`
  for more), plus the `loomground` governance-language route registered the same
  way (so `METHODS` holds 20 entries in total).
- The LLM-interpretation bridge, tamper-evident replayable provenance (signable
  via an injected host signer; the default is a SHA-256 content digest), and a
  verifier data-pump (verified runs → training data).
- A conforming Loomground language implementation and first-class nD route:
  parse `.lg`, validate the policy graph, evaluate transports, reproduce the
  canonical observation and map governance outcomes into the bounded Solver
  decision space.

The [vision](docs/design/vision.md) states the intent this code serves; the
[operations guide](docs/guides/operations.md) explains how to run it
and wire it into host and Versum.

## Install and prove it

```bash
python3 -m pip install -e . --break-system-packages   # or into a venv
python3 -m pytest -q                                   # expect: 463 passed
```

The two load-bearing gates:

- `tests/test_dependency_inversion.py` — the package imports **no** governance and
  **no** domain module, and carries no domain literal in executable code. **This
  passing is the definition of "universal."**
- `tests/test_api_parity.py` — every public symbol the host modules exposed is
  re-exported by the matching package module.

## Use

```python
from loomground_solver import entail, check, narrow, fingerprint, decision_space

# narrow an unknown problem by inference over a federation of fingerprint pairs
out = narrow(problem_fp, federation)   # {solution, escalate, determinacy, complete}
```

Host-side glue (a `NormSource` over a corpus, a `Governance` over a policy engine)
lives outside this package and is injected through `loomground_solver.ports`.

To verify candidates from any skill or graph through the neutral protocol:

```bash
loomground-solver manifest
loomground-solver verify request.json
loomground-solver loomground policy.lg --transport transport.json
```

Or use the transport-neutral facade in process:

```python
from loomground_solver import default_service

result = default_service().verify(reasoning_request_dict)
```

The standalone service verifies evidence embedded under
`extensions.inline_evidence`. A host can inject its own `EvidenceProvider` and
`StructuralCompiler`; neither adapter needs to live in Solver.

## License

Licensed under the Apache License, Version 2.0. See `LICENSES/Apache-2.0.txt` and `NOTICE`.

## Authorship

This work is authored by **Loomground Contributors** and was assisted by Claude and Codex. Claude
and Codex are acknowledged as tools, not authors or co-authors.
