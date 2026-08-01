# Ecosystem release and version administration

Loomground is the shared language and contract upstream. Solver and Versum are
sibling implementations of that contract. RVND is the governed product that
integrates both.

```text
loomground-governance ─┬─> loomground-solver ─┬─> rvnd
                     └─> versum ────────┘
```

## Two independently-versioned artifacts in this repository

This repository ships two artifacts, versioned independently, so their
version numbers are expected to differ and should not be read as a
contradiction:

- **The Python kernel** (`loomground-solver`, tracked in `pyproject.toml` and
  `.release-please-manifest.json`, currently `0.1.0`). Release Please derives
  its version from conventional commits on `main`, as described in
  [Release PRs](#1-release-prs) below.
- **The Claude plugin bundle** (tracked in `package.json` and
  `.claude-plugin/plugin.json`, currently `0.3.0`). Its version is bumped by
  hand in both files when the bundled skills change; it does not go through
  Release Please and does not track the kernel's version.

## Policy

- `main` is the ecosystem integration line. Nightly and pull-request
  conformance runs test every tool against the current Loomground `main`.
- A stable release is immutable. Solver and Versum releases consume a published
  compatible `loomground-governance` version; RVND consumes published compatible
  Solver and Versum versions.
- Libraries declare compatible ranges. RVND deployment locks the exact resolved
  versions.
- A release is promoted only after the downstream compatibility suite passes.

Example release metadata:

```toml
# Solver and Versum
dependencies = ["loomground-governance>=0.8,<0.9"]

# RVND
dependencies = [
  "loomground-governance>=0.8,<0.9",
  "loomground-solver>=0.1,<0.2",
  "loomground-versum>=0.6,<0.7",
]
```

Example RVND deployment lock:

```text
loomground-governance==0.8.2
loomground-solver==0.1.3
loomground-versum==0.6.4
rvnd==0.6.8.2
```

## Automated administration

Use the same four controls in every repository.

### 1. Release PRs

Install Release Please in each repository. Conventional commits determine the
next semantic version and generate a reviewed release PR containing the version
change and changelog:

- `fix:` increments the patch version.
- `feat:` increments the minor version.
- `feat!:` or a `BREAKING CHANGE:` footer increments the major version.
- `docs:`, `test:`, `ci:` and `chore:` do not independently require a release.

Merging the generated release PR creates the release tag. Humans approve the
version; automation performs the bookkeeping.

### 2. Build and publish

On the release tag, GitHub Actions must:

1. check out the tagged source;
2. install from clean package metadata;
3. run unit, dependency-inversion and Loomground conformance gates;
4. build the wheel and source distribution once;
5. publish those exact artifacts with PyPI Trusted Publishing;
6. retain build provenance and attestations.

Production publication must use a protected GitHub environment named `pypi`
and pass the RVND governance lane. No long-lived PyPI API token belongs in the
repository.

### 3. Dependency propagation

Enable Dependabot for the `pip` and `github-actions` ecosystems. A newly
published Loomground version then opens dependency PRs in Solver and Versum; new
Solver and Versum versions open PRs in RVND. Configure
`versioning-strategy: increase-if-necessary` so compatible ranges are not
rewritten unnecessarily.

Every dependency PR runs the full consumer compatibility suite. It may merge
automatically only for a patch update when all required checks pass. Minor and
major updates require human approval.

### 4. Cross-repository compatibility

A Loomground release is not ecosystem-complete merely because its own tests
pass. After publishing it, dispatch compatibility runs in Solver and Versum.
After both publish compatible releases, dispatch RVND's integration suite.

Use a GitHub App with narrowly scoped access for cross-repository dispatch. Do
not use a personal access token. Keep the promotion state visible through one
compatibility matrix:

| Component | Released line | Loomground contract | Downstream gate |
| --- | --- | --- | --- |
| Loomground language | `0.8.x` | `0.8` | Solver + Versum |
| Solver | `0.1.x` | `0.8` | RVND |
| Versum | `0.1.x` | `0.8` | RVND |
| RVND | `0.1.x` | `0.8` | deployment smoke test |

## Release order

1. Merge compatible work to Loomground `main`.
2. Merge the Loomground release PR and publish `loomground-governance`.
3. Accept the generated dependency PRs in Solver and Versum after conformance.
4. Merge their release PRs and publish both packages.
5. Accept the generated Solver and Versum dependency PRs in RVND.
6. Regenerate RVND's lock file, run the integration suite and publish RVND.
7. Advance development versions on `main` and continue nightly conformance.

## Required branch protection

- No direct pushes to `main`.
- Require the release gate and conformance checks.
- Require one approving review for ordinary changes and release PRs.
- Require code-owner review for language schemas, public contracts and release
  workflows.
- Prevent tag deletion and modification.
- Restrict the `pypi` environment to protected tags and required reviewers.

The result is automatic administration, not automatic authority: tooling
calculates versions, creates PRs, propagates dependencies and publishes approved
artifacts, while compatibility and human review control promotion.

## Is this best practice?

This is a strong and widely used foundation, but it becomes a release-grade best
practice only when all of the controls below are active.

Already in the design:

- release changes pass through reviewed pull requests;
- versions communicate compatibility through semantic versioning;
- unit and Loomground conformance checks gate publication;
- PyPI Trusted Publishing avoids permanent repository credentials;
- a protected GitHub environment retains publication approval;
- dependency upgrades arrive as visible, tested pull requests; and
- RVND locks the exact versions used in deployment.

### Required hardening

#### Do not release stable packages against `main`

Solver and Versum may test against Loomground `main` continuously, but their
stable distributions should declare a compatible published version:

```toml
dependencies = ["loomground-governance>=0.8,<0.9"]
```

Testing `main` answers, "Will tomorrow's ecosystem still work?" A stable
dependency answers, "Can today's release be installed again?" Both checks are
needed, but they serve different purposes.

#### Gate the release pull request before tagging

The safe sequence is:

```text
release PR -> required checks -> approval -> merge -> tag -> build -> publish
```

The ordinary release gate must be a required check on Release Please pull
requests. Testing after tag creation remains useful as defence in depth, but it
must not be the first point at which a proposed release is validated.

#### Build once

Build the wheel and source distribution once from the tagged source, retain
their hashes and publish those same artifact bytes after approval. Rebuilding
between approval and publication weakens the link between the tested and
published package.

#### Pin workflow dependencies

Third-party GitHub Actions should be referenced by full commit SHA instead of a
movable major tag. Dependabot can update those SHA references through reviewed
pull requests. This protects the release pipeline itself from unexpected action
changes.

#### Record provenance

Every release record should contain:

- the source commit and signed release tag;
- the Loomground contract version;
- Python versions tested;
- unit, conformance and integration results;
- wheel and source-distribution hashes; and
- the identity of the publishing workflow.

#### Protect release administration

Apply RVND policy and branch protection to at least:

```text
/pyproject.toml
/.github/workflows/
/release-please-config.json
/.release-please-manifest.json
```

Changes to public contracts, version policy and publishing authority must pass
the automated RVND release policy.

## Alternatives

| Approach | Advantages | Weaknesses | Best fit |
| --- | --- | --- | --- |
| Release Please | Reviewed version and changelog PRs; transparent automation | Requires disciplined commit messages | This ecosystem |
| `setuptools-scm` | Derives the package version from immutable Git tags | Needs separate changelog and release coordination | Tag-led Python libraries |
| Python Semantic Release | Automates version, changelog, tag and publication | Grants more authority to automation and can be brittle | Teams accepting unattended releases |
| Hatch, Poetry or PDM | Integrated environment, version, build and publish tooling | Introduces a tool-specific workflow and lock model | Teams standardising on one Python tool |
| Manual tags and Actions | Simple and has few moving parts | Version and changelog errors remain manual | Small projects with rare releases |
| Calendar versioning | Makes release recency obvious | Does not communicate compatibility impact | Data and specification snapshots |
| Monorepo | Enables atomic contract and implementation changes | Increases coupling and coordinated-release complexity | Components that must always change together |

### Release Please versus `setuptools-scm`

`setuptools-scm` is the strongest simple alternative. A Git tag becomes the
single version source, so no tool edits a version field. It is attractive for
independent Python libraries.

Release Please is a better fit for Loomground's multi-repository contract chain
because it makes the proposed version and changelog visible before the release
exists. That review point matters when a language change may propagate through
Solver, Versum and RVND.

## Recommended target state

```text
conventional commits
        |
        v
Release Please pull request
        |
        v
required unit + conformance + integration checks
        |
        v
human approval and merge
        |
        v
immutable signed tag
        |
        v
one artifact build with provenance
        |
        v
protected PyPI Trusted Publishing
        |
        v
tested dependency pull requests in downstream repositories
        |
        v
exact RVND deployment lock
```

Release Please administers the process. Compatibility gates and reviewers retain
authority over whether a release is allowed to progress.
