<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Security policy

## Supported versions

loomground-solver is currently pre-1.0. Security fixes are made on the latest
release line only.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private
vulnerability reporting for this repository. Include the affected version or
commit, reproduction steps, impact, and any suggested mitigation. Please allow
the maintainer time to investigate before public disclosure.

This repository ships a standard-library-only reasoning and decision kernel —
a parser, validator and evaluator for the Loomground language, a fingerprint
and federation model, and universal system-adapter boundaries — with no
network service of its own and no governance or corpus code (both arrive only
through host-injected ports). A vulnerability report against this repository
is most likely to concern the Loomground parser or evaluator, the adapter
boundary (`src/loomground_solver/adapters/`), the pinned dependency on
`loomground-governance`, or the build and release pipeline; please say which of
these is affected.
