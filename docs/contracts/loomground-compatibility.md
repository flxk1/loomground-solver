# Loomground compatibility

Solver implements Loomground as a deterministic nD language route.

| Solver language identifier | Accepted input | Conformance basis |
| --- | --- | --- |
| `0.7` | Released v0.7 language | Loomground manifest `0.7` |
| `0.8.2` | Released v0.8.2 language | Loomground `v0.8.2` conformance vectors |

Solver accepts `0.7` and the published `0.8.2`. A request must name one of
these two versions; Solver never silently upgrades an unrequested version.

The `0.8.2` row above is illustrative, not a hardcoded constant: Solver derives
`SUPPORTED_LANGUAGE_VERSIONS` at runtime from whichever `loomground-governance`
version is actually installed (see `language_version()` in
`src/loomground_solver/loomground.py`), so an installed prerelease or patch
build is reflected automatically rather than silently diverging from this
table.

The normative grammar, schemas, vocabulary and vectors remain owned by the
Loomground specification repository and arrive through its data-only
`loomground-governance` package. Solver ships an independent implementation, not
an artifact snapshot. Its release gate uses the package's neutral protocol and
conformance runner through `scripts/run_loomground_conformance.py`.

A Solver release pins a compatible published `loomground-governance` version
(`>=0.8,<0.9`, resolved in CI through `requirements-dev.txt`'s pinned tag) —
it does not depend on the language repository's `main` branch. `main` is the
ecosystem's declared integration line (`docs/guides/releasing.md`, "Do not
release stable packages against `main`"): the term names where a *future*
continuous-conformance line against the language repository's latest commit
would run, not this repository's release dependency, and not (yet) a job
this repository runs. The release record must capture the resolved
`loomground-governance` version tested by CI.

Graphs remain language-neutral. Loomground parsing and evaluation do not alter
or extend a graph schema.
