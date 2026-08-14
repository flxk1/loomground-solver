# loomground-solver — RUNBOOK

The universal reasoning/decision kernel, extracted from host into a standalone package that **host and the KG (Versum) both import** without owning it. Governance and corpus arrive only through injected ports, so the same kernel runs as: the KG's L3 (may write derived truth), the standalone path-solver (writes nothing), and host's clamped verdict instance.

The release gate currently contains **463 tests**; the package imports in an empty environment with no governance/domain leak. The host-side integration (shims + adapters + their tests) lives in the host repo; every public host symbol is re-exported by the shims there.

## What's in the bundle

```
loomground-solver/
  pyproject.toml
  loomground_solver/           # the package (2.7k LOC, stdlib-only)
    dimensions.py              # 5D edge model + composition algebra (pure)
    reasoning.py               # path composition over the 5D graph — the epistemic solver
    norm_contract.py           # PASS/VIOLATION/ESCALATE floor (NT-* invariants)
    temporal.py  predicate.py  # leaf deps of norm_contract
    contract.py                # the universal justified-answer contract (R1–R8) + profiles
    phases.py                  # phase briefs (was reasoning_phases)
    topology.py                # the derived-solver DAG validator (was solver_topology)
    _projection.py             # the _node/_edge/validate_graph helpers (from kg_export)
    case.py                    # CaseRecord/Ground/Fact + project_pairs (pure subset of problem_kg)
    ports.py                   # NormSource, ModelFn, Governance (Protocols) + NullGovernance
    api.py                     # solve/entail/plan/check surface
    __init__.py
  tests/                       # the test suite, incl. the dependency-inversion gate
  README.md  docs/
```
(The host-side glue — the shims and host adapters — lives in the host repo at
`loomground-solver-integration/`, not here. The solver depends on none of it.)

## Install + prove the package (anywhere)

```bash
cd loomground-solver
python3 -m pip install -e . --break-system-packages   # or into a venv
python3 -m pytest -q                                   # expect: 463 passed
python3 scripts/run_loomground_conformance.py           # expect: 47/47 vectors passed
python3 -m build                                        # build sdist + wheel
```

The two gate tests are the load-bearing ones:
- `tests/test_dependency_inversion.py` — the package imports **no** governance (`policy`, `lock`, `decision_surface`, `mutation_log`, `signing`) and **no** domain module (`rule_extractor`, `rule_registry`, `legal_*`, `hohfeld`, `kg_export`, `workspaces`). **This passing is the definition of "universal."**
- `tests/test_api_parity.py` — every public symbol host's modules exposed is re-exported by the matching package module.

## Wire host to import it — and lose nothing (run this in your Terminal)

The host glue lives in the host repo at `loomground-solver-integration/`. Its `rvnd_shims/workspaces/*.py` replace six host module bodies with re-exports from the package, so every old `workspaces.reasoning* / norm_contract / dimensions / solver_topology` import keeps resolving; `reasoning_contract`'s `check_folder_case` is kept in the shim (it still reads `policy`), so host behaviour is identical.

```bash
cd /path/to/host/server
python3 -m pip install -e /path/to/loomground-solver     # make the package importable
# back up, then drop the shims over the module bodies:
cp -r ../loomground-solver-integration/rvnd_shims/workspaces/* src/workspaces/
python3 -m pytest -q                                     # THE FINAL GATE: full host suite green
```

This full-suite run is the definitive "host loses nothing" check. It could not be closed from the cloud because the `problem_kg` / `reasoning_walker` / `*_audit` / `*_facade` tests pull in `rule_registry`, `legal_corpus`, `memory`, `mcp_server`, `policy`, and `lock` — roughly half the 216-module server. If any test fails, it will name a symbol the shim did not re-export; send it to me and I'll patch the shim.

## Wire the KG (Versum) to import it — symmetric

Versum imports the same package as its L3 apex. Implement `NormSource` over the claim layer (join on `canonical_urn`) and call `entail(...)` / `check(..., governance=<terrain-write>)`. Nothing in `versum/` imports the solver's internals — same one-way, port-only contract as host.

## Adapters — how the KG and host plug in

Packaged adapters live under `loomground_solver.adapters`:

- `VersumNormSource` reads native Versum claims, typed compositions, nD
  assignments and bindings. It projects deontic and conditional fields used by
  Solver while retaining the complete native records on each span.
- `install_reference_filters()` installs the statistics-methods and Walton
  argumentation-schemes fingerprint adapters explicitly.
- `SystemAdapter` and `AdapterRegistry` remain the typed boundary for systems
  that project observations to Solver 5D+nD input. Corpus ports and fingerprint
  filters use their own contracts instead of pretending to be system adapters.

The fingerprint and Versum adapters live in the package under
`loomground_solver.adapters`; there is no separate `integrations/`
compatibility layer.

In the **host** repo (`loomground-solver-integration/adapters_rvnd/`), with their tests:
- `RvndNormSource` — `NormSource` over `workspaces.rule_registry.RuleRegistry`.
- `RvndGovernance` — `Governance` over host: oversight from `policy.load_policy` (level + opt-out), custody from `lock_classify`, audit via `mutation_log.append_raw`; lazy host imports, every dep injectable.

The proofs the adapter tests carry: injecting a `Governance` vs `NullGovernance` **moves the R4 judgment floor** (autonomous → VIOLATION on Esc∧Stake; approve → escalate), and a `NormSource`'s spans **flow into 5D reasoning** (`entail`) end-to-end.

## Known seams / deferred (not done here, by design)

- **NT-6 / NT-14 legal vocab inlined.** `norm_contract` carries two legal-domain checks (Hohfeld incidents; per-system conflict principles). To keep behaviour byte-faithful without importing `hohfeld` / `legal_systems`, their closed sets are inlined as module-level defaults in `norm_contract.py` (marked `FOLLOW-UP`). The clean end-state promotes them to an **injected legal profile** — a small refactor, not a behaviour change.
- **Corpus-coupled functions deferred:** `problem_kg.build_case` / `gate_case` / `derive_actions`, the `reasoning_walker`, and `check_folder_case` stay on the host side (they need `rule_registry` / `legal_corpus` / `policy`). The package ships the pure `CaseRecord` model and the ports they will plug into.
- **Built since the extraction:** the scenario/possible-worlds rung + grounded defeasible resolution (`scenario.py`, `rulepacks.py`), the deterministic decision space (`decision.py`), signed replay (`replay.py`), the pluggable-filter fingerprint (`fingerprint.py`), subsumption + end-to-end rule reasoning (`subsumption.py`), the 19-method reasoning registry (`methods/`), the LLM-interpretation bridge (`interpret.py`), and the verifier data-pump (`datapump.py`). This RUNBOOK's bundle tree above is illustrative and does not list every module.
