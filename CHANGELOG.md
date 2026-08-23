<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Changelog

## [0.6.0](https://github.com/flxk1/loomground-solver/compare/solver-v0.5.0...solver-v0.6.0) (2026-08-23)


### Features

* **engine:** language 0.11.0 conformance + PROM-001 integrity ([2b331d7](https://github.com/flxk1/loomground-solver/commit/2b331d79871a3bac5a7ace4ebf1b7d03fd1bfd4e))
* **engine:** language 0.11.0 conformance + PROM-001 integrity ([151321f](https://github.com/flxk1/loomground-solver/commit/151321f81f5bae4b7206385c45b067d96161e8b3))

## [0.5.0](https://github.com/flxk1/loomground-solver/compare/solver-v0.4.0...solver-v0.5.0) (2026-08-18)


### Features

* **epistemic:** surface the root presupposition, not its consequences ([84f6542](https://github.com/flxk1/loomground-solver/commit/84f6542465b38859355ee3a022f422a8f81cb4bd))


### Developed here, moved out before release

Six features were built on this branch and then moved into their own
repositories. **They are not part of 0.5.0 and were never published from this
package** — no released version of `loomground-solver` has ever contained them.
They are listed because their commits are in this range, not because anything
here ships them.

The reason for the move: this package's claim is that it holds no subject areas,
and agentic oversight is a subject area. Each now sits *above* the kernel,
depending on the shared verdict, the OPEN-dominant fold and the injected ports.

| Was | Now |
|---|---|
| `oversight` ([18bf510](https://github.com/flxk1/loomground-solver/commit/18bf510f5881057cc546b0ad44d5f74c08451dfa)) | [`loomground-brief`](https://github.com/flxk1/loomground-brief) |
| `divergence` ([811addb](https://github.com/flxk1/loomground-solver/commit/811addb7a1bd435b20ed1bf09eaf408197f3ae95)) | [`loomground-mandate`](https://github.com/flxk1/loomground-mandate) |
| `escalation` ([2c38935](https://github.com/flxk1/loomground-solver/commit/2c38935acae61eb1ac70d8beb71d0d226818eddd)) | [`loomground-escalation`](https://github.com/flxk1/loomground-escalation) |
| `proxy` ([4752d95](https://github.com/flxk1/loomground-solver/commit/4752d9551e4544819eb06f178077d5d769b2119a)) | [`loomground-proxy`](https://github.com/flxk1/loomground-proxy) |
| `falsifiability` ([29e1f19](https://github.com/flxk1/loomground-solver/commit/29e1f19ecbe2ea7436e5fd9728e6d4937aab13a7)) | [`loomground-falsifiability`](https://github.com/flxk1/loomground-falsifiability) |
| `collapse` ([ef8b980](https://github.com/flxk1/loomground-solver/commit/ef8b9809464278b56bfad194a65687cf9c7cefb4)) | [`loomground-collapse`](https://github.com/flxk1/loomground-collapse) |

The fix *stop shipping a ladder, and ground divergence via the port*
([419dd0a](https://github.com/flxk1/loomground-solver/commit/419dd0a43ebdf99ba1b73da7af2a2e815a9774bf))
applied to two of the above and travelled with them. The move itself is
[08b0664](https://github.com/flxk1/loomground-solver/commit/08b0664).


### Documentation

* **roadmap:** reasoning work for agentic oversight ([c36866b](https://github.com/flxk1/loomground-solver/commit/c36866bad1dbb89848ee4551c171eb87d65f2f7d))
* **roadmap:** reasoning work for agentic oversight ([281aa33](https://github.com/flxk1/loomground-solver/commit/281aa33eefce83f84287ccc500196e619f567225))

## [0.4.0](https://github.com/flxk1/loomground-solver/compare/solver-v0.3.0...solver-v0.4.0) (2026-08-10)


### Features

* panel_e2e — end-to-end deontic lane over the real planes ([5500498](https://github.com/flxk1/loomground-solver/commit/5500498eec69aefbc145b27271758f19a87865cb))
* validity-level e2e + span-exact deadline trim (aliases -&gt; 0) ([696d7d4](https://github.com/flxk1/loomground-solver/commit/696d7d453eaa632b9dbc8f27179489efd50ab796))

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
