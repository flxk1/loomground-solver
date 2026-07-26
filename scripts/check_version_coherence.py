#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Version-coherence gate.

This repository carries three independent version axes (see ``RELEASING.md``
for the full explanation):

1. Package/release — ``pyproject.toml`` and ``.release-please-manifest.json``
   (currently 0.1.0). Release Please manages this axis from conventional
   commits on ``main``.
2. Contract/protocol — ``reasoning.interop/1.0``, the claim-axes vocabulary,
   and ``verifier_version`` in code. Frozen; never bumped by a package
   release.
3. Plugin/distribution — ``package.json`` and ``.claude-plugin/plugin.json``
   (currently 0.3.0). Bumped by hand when the bundled skills change.

This checker keeps axis 1 internally consistent (pyproject.toml agrees with
the release-please manifest) and axis 3 internally consistent (package.json
agrees with the plugin manifest). It deliberately never compares axis 1 to
axis 3 — the plugin version is not expected to equal, and must not be forced
to equal, the package version.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("pyproject.toml has no top-level version field")
    return match.group(1)


def _json_field(path: str, field: str) -> str:
    data = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if field not in data:
        raise SystemExit(f"{path} has no {field!r} field")
    return data[field]


def main() -> int:
    errors: list[str] = []

    package_version = _pyproject_version()
    manifest_version = _json_field(".release-please-manifest.json", ".")
    if package_version != manifest_version:
        errors.append(
            "package/release axis drift: pyproject.toml version="
            f"{package_version!r} != .release-please-manifest.json[\".\"]="
            f"{manifest_version!r}"
        )

    plugin_bundle_version = _json_field("package.json", "version")
    plugin_manifest_version = _json_field(".claude-plugin/plugin.json", "version")
    if plugin_bundle_version != plugin_manifest_version:
        errors.append(
            "plugin/distribution axis drift: package.json version="
            f"{plugin_bundle_version!r} != .claude-plugin/plugin.json version="
            f"{plugin_manifest_version!r}"
        )

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1

    print(
        f"version coherence ok: package/release={package_version!r} "
        f"plugin/distribution={plugin_bundle_version!r} (independent axes, "
        "not compared to each other)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
