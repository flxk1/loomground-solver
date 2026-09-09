# loomground-solver

Shared reasoning kernel: composes 5D edges, verifies defeasible reasoning and returns a bounded decision, with governance and corpus injected through ports.

## Install

```bash
pip install -r requirements-dev.txt   # pinned loomground-governance + loomground-deontic
pip install .                         # installs the `loomground-solver` command
python -m pytest -q
```

## Usage

```python
from loomground_solver import entail, check, narrow, fingerprint, decision_space, default_service

out = narrow(problem_fp, federation)          # {solution, escalate, determinacy, complete}
result = default_service().verify(request)    # reasoning.interop 1.0 request dict
```

```bash
loomground-solver manifest
loomground-solver verify request.json
loomground-solver loomground policy.lg --transport transport.json
```

## Interface

| Element | Definition |
| --- | --- |
| Inputs | reasoning pairs on the 5D edge model (structural · causal · intentional · temporal · relational); cases and rule-packs; `ReasoningRequest` (`reasoning.interop` 1.0, `reasoning.edges/v1`, inline evidence under `extensions.inline_evidence`); `.lg` policy + transport |
| Outputs | justified answer `PASS` \| `VIOLATION` \| `ESCALATE`; decision space `accepted` \| `undecided` \| `rejected`; fingerprint (open nD family); `ReasoningResult` with a replayable signed trace |
| Ports (`loomground_solver.ports`) | `NormSource` · `EvidenceProvider` · `CandidateProvider` · `StructuralCompiler` · `ReasoningService` · `Governance` (default `NullGovernance`) · `Signer` |
| Dependency direction | solver imports the data-only `loomground-governance` kit and `loomground-deontic`; graphs and hosts import solver; `tests/test_dependency_inversion.py` fails on any graph, governance-engine or domain import inside the package |
| Extension points | `register_method` (20 registered methods) · `SystemAdapter` + `AdapterRegistry` (built-in: loomground, versum corpus, deontic, filters) · `addons/` (advisor, metacognition, world_model) |

Contracts: [reasoning-interop](docs/contracts/reasoning-interop.md) · [loomground-compatibility](docs/contracts/loomground-compatibility.md). Running it: [docs/guides/operations.md](docs/guides/operations.md).

## Family

Shared reasoning kernel.

- consumes: [loomground-governance](https://github.com/flxk1/loomground-governance) `>=0.8,<0.12` · [loomground-deontic](https://github.com/flxk1/loomground-deontic) `>=0.1,<0.2`
- consumed by: [loomground-versum](https://github.com/flxk1/loomground-versum) (corpus adapter, `reasoning.interop`) · loomground-norm · loomground-legal · the diagnostic operators (brief, collapse, escalation, falsifiability, mandate, proxy) · RVND
- pipeline: `source → loomground-ingest → loomground-versum → loomground-solver → applied or diagnostic planes`

Kernel intent, adapter history and compatibility policy: [docs/design/overview.md](docs/design/overview.md).

## Status

- version 0.5.0 · `reasoning.interop` 1.0 · Loomground language 0.7 – 0.11.0 (`SUPPORTED_LANGUAGE_VERSIONS`)
- 1084 tests passed, 21 skipped (`python -m pytest -q`)
- python >=3.10 · 7 skills (`skills/`) · 300 public symbols (`loomground_solver.__all__`)

## License

Apache-2.0 — `LICENSES/Apache-2.0.txt`, `NOTICE`.
