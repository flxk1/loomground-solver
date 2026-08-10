<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Changelog

## [0.3.0](https://github.com/flxk1/loomground-solver/compare/solver-v0.2.0...solver-v0.3.0) (2026-08-09)


### Features

* graded panel — DoD acceptance over statutes/contracts/policies ([2f0c9f4](https://github.com/flxk1/loomground-solver/commit/2f0c9f4cd975d929e07245f773074ac9341cb1f8))
* scale compose_paths for large regulation graphs ([#9](https://github.com/flxk1/loomground-solver/issues/9)) ([8bfbf44](https://github.com/flxk1/loomground-solver/commit/8bfbf44850626acd0c4a9710b2b7aae1d2094032))

## [0.2.0](https://github.com/flxk1/loomground-solver/compare/solver-v0.1.3...solver-v0.2.0) (2026-08-02)


### Features

* add off_grid fingerprint filter for un-coordinated relations ([d4adbae](https://github.com/flxk1/loomground-solver/commit/d4adbae769bfe1a6e3646427a0019ffe94ff64f2))


### Documentation

* correct test counts, language version, and provenance wording ([ea4d95f](https://github.com/flxk1/loomground-solver/commit/ea4d95fd5a3e2a69ccaec188e7709abe97cf3411))
* correct test counts, language version, and provenance wording ([2cc761d](https://github.com/flxk1/loomground-solver/commit/2cc761d65eadab78ba99bb272f9473558dc89f71))

## [0.1.3] - 2026-07-26

- Pin the privacy-clean Governance and Deontic publication roots.

All notable release changes are documented here. Versions follow Semantic Versioning
while the project is pre-1.0; a minor release may intentionally change compatibility.

## [Unreleased]

## [0.1.2] - 2026-07-25

### Added

- A built-in Deontic adapter as a second consumed language.

### Fixed

- Require host-authorized add-on factories so optional extensions cannot
  silently broaden execution authority.

## [0.1.1] - 2026-07-25

### Changed

- Depend on `loomground-governance` (the renamed upstream language distribution)
  instead of `loomground-language`, resolved from its `v0.8.0` release.

### Added

- A version-coherence gate and a register-cleanliness gate in CI.

## [0.1.0] - 2026-07-24

The first published release: a standard-library-only reasoning and decision kernel,
packaged so a knowledge graph and a governance layer can import it without owning it.

### Added

- A 5D edge model and composition algebra (structural / causal / intentional /
  temporal / relational) and path composition over the dimensioned graph — the
  epistemic solver.
- A justified-answer contract (`PASS` / `VIOLATION` / `ESCALATE`) with profiles, and
  a deterministic decision space (`accepted` / `undecided` / `rejected`).
- Subsumption and end-to-end rule reasoning (Tatbestand -> Rechtsfolge + exception),
  scenario/possible-worlds resolution with grounded (reinstatement-sound)
  defeasibility, and rule-packs.
- A pluggable-filter fingerprint (an open nD family) and federation: narrowing an
  unknown problem's solution by inference over a body of problem-solution
  fingerprint pairs, escalating rather than guessing coordinates the federation does
  not pin down.
- An open registry of 19 reasoning methods across logic, philosophy, methodology,
  rationalist decision theory, mathematics, and data science.
- The LLM-interpretation bridge, signed replayable provenance, and a verifier
  data-pump (verified runs -> training data).
- A conforming Loomground language implementation (`src/loomground_solver/loomground.py`):
  parser, well-formedness validator, token validator, transport evaluator, and
  observation projection, gated by the language's own conformance vectors.
- A universal system-adapter boundary (`src/loomground_solver/adapters/`): the
  built-in Loomground reference adapter, the Versum corpus adapter and claim-axes
  companion decoder, and an `AdapterRegistry` for third-party adapters — none
  privileged over another by name.
- Optional add-ons: deterministic metacognition (read-only observation and
  recurring-gap proposals) and a bounded world model (belief updates and immutable
  context snapshots), both excluding any runtime, mutation, or auto-approval
  behavior.
- Two load-bearing gates: `tests/test_dependency_inversion.py` (the package imports
  no governance and no domain module) and `tests/test_api_parity.py` (every public
  symbol a consuming host expects is re-exported by the matching package module).
- A `loomground-solver` CLI (`manifest`, `verify`, `loomground`) and an in-process
  transport-neutral facade (`default_service()`).

### Known limitation

- The package declares a pinned, compatible range for `loomground-governance`
  (`>=0.8,<0.9`); it does not track that repository's `main` branch. A future
  continuous-conformance line against `main` is ecosystem policy
  (`docs/guides/releasing.md`) but is not yet wired into this repository's CI.
