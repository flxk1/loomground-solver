<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Releasing

This document is self-contained: read it without needing any other file to understand
how a release of this repository happens.

## Three independent version axes

This repository carries three version numbers that look similar but answer different
questions, and none of them should be collapsed into another:

1. **Package/release** — `pyproject.toml` and `.release-please-manifest.json` share
   one number (currently `0.1.0`). This is the version PyPI installs and the version
   this document's release flow manages. `scripts/check_version_coherence.py` gates
   that the two stay equal.
2. **Contract/protocol** — `reasoning.interop/1.0`, the claim-axes vocabulary
   (profile `0.1.0`), and `verifier_version "0.1.0"` named in code. These are frozen
   independently of the package release and change only when the governed contract
   itself changes, never as a side effect of a package release.
3. **Plugin/distribution** — `package.json` and `.claude-plugin/plugin.json`
   (currently `0.3.0`). This is the companion-skill bundle's own version; it is
   bumped by hand when the bundled skills change and never needs to equal the
   package version above. `scripts/check_version_coherence.py` gates that these two
   manifests agree with *each other*, never that either equals the package version.

A release bumps axis 1. It must never bump axis 2, and it bumps axis 3 only if the
bundled skills themselves changed.

## Release flow (Release Please)

[Release Please](https://github.com/googleapis/release-please) turns conventional
commits on `main` into a reviewed release pull request:

- `fix:` increments the patch version.
- `feat:` increments the minor version.
- `feat!:` or a `BREAKING CHANGE:` footer increments the major version.
- `docs:`, `test:`, `ci:`, and `chore:` do not by themselves trigger a release.

Merging the generated release pull request updates `pyproject.toml` and
`CHANGELOG.md`, and creates a component-prefixed tag of the form `solver-vX.Y.Z` (for
example, the existing `solver-v0.1.0` tag) — the prefix distinguishes this package's
releases from sibling repositories that share the same ecosystem's conventions.
Configuration lives in `release-please-config.json` and
`.release-please-manifest.json`; the workflow is
`.github/workflows/release-please.yml`.

Humans approve the version by approving the release pull request; automation only
performs the bookkeeping (computing the version, updating the changelog, creating the
tag).

## Publishing (PyPI Trusted Publishing)

Once the release pull request merges and the tag is created, the `publish` job in
`.github/workflows/release-please.yml` installs the pinned development dependency set
(so the abstract `loomground-governance>=0.8,<0.9` range in `pyproject.toml` resolves
without needing an index), runs the test suite and the Loomground conformance check,
builds the source distribution and wheel once, and publishes them using
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — an OIDC
exchange (`id-token: write`) instead of a long-lived API token stored in the
repository. Publication runs only inside the protected `pypi` GitHub environment and
must pass the host governance lane before anything reaches PyPI.

## Ecosystem release order (reference only — not required by this repository alone)

This package is one of several sibling implementations of the shared Loomground
contract. When a change needs to reach the whole ecosystem, the usual order is:

1. Merge the change to the language repository's `main` and publish the new
   `loomground-governance` version.
2. This repository picks up the new version through its own Dependabot pull request,
   gated by its own conformance suite.
3. This repository cuts its own release once the dependency update passes.
4. Downstream consumers (for example, host) pick up the new `loomground-solver`
   version through their own dependency pull requests.

This repository's own release does not wait on that downstream propagation; it is
listed here so a reader understands what a release here sets in motion. The full
policy lives in `docs/guides/releasing.md`.

## Local verification before tagging

```
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
python3 scripts/run_loomground_conformance.py
python3 scripts/check_version_coherence.py
python3 scripts/check_adapter_selection_neutrality.py
reuse lint
python3 -m build
```

All of the above run in CI (`.github/workflows/release-gate.yml`) on every push and
pull request; a release pull request must pass them before it merges.

## Definition of done

`docs/RELEASE-DoD.md` is the repository-agnostic checklist this repository is
expected to satisfy. It is safe to copy unchanged into sibling repositories.
