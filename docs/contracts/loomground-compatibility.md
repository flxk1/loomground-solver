# Loomground compatibility

Solver implements Loomground as a deterministic nD language route.

| Solver language identifier | Accepted input | Conformance basis |
| --- | --- | --- |
| `0.7` | Released v0.7 language | Loomground manifest `0.7` |
| `0.8.2` | Released v0.8.2 language | Loomground `v0.8.2` conformance vectors |
| `0.9` | Released v0.9 language | Loomground `v0.9.0` conformance vectors |
| `0.10` | Released v0.10 language | Loomground `v0.10.0` conformance vectors |
| `0.11` | Released v0.11 language | Loomground `v0.11.0` conformance vectors |

A request must name one of these versions; Solver never silently upgrades an
unrequested version.

The rows above are illustrative, not a hardcoded constant: Solver derives
`SUPPORTED_LANGUAGE_VERSIONS` at runtime from whichever `loomground-governance`
version is actually installed (see `language_version()` in
`src/loomground_solver/loomground.py`), so an installed prerelease or patch
build is reflected automatically rather than silently diverging from this
table.

The normative grammar, schemas, vocabulary and vectors remain owned by the
Loomground specification repository and arrive through its data-only
`loomground-governance` package. Solver ships an independent implementation, not
an artifact snapshot. Its release gate uses the package's neutral protocol and
conformance runner through `tools/run_loomground_conformance.py`.

A Solver release pins compatible published packages — `pyproject.toml` declares
`loomground-governance>=0.8,<0.12` and `loomground-deontic>=0.1,<0.3`, resolved
in CI through the commits `requirements-dev.txt` pins (governance `v0.11.0`,
deontic `v0.2.0`). It does not depend on either language repository's `main`
branch. `main` is the ecosystem's declared integration line
(`docs/guides/releasing.md`, "Do not release stable packages against `main`"):
the term names where a *future* continuous-conformance line against the
language repository's latest commit would run, not this repository's release
dependency, and not (yet) a job this repository runs. The release record must
capture the resolved `loomground-governance` and `loomground-deontic` versions
tested by CI.

Graphs remain language-neutral. Loomground parsing and evaluation do not alter
or extend a graph schema.
