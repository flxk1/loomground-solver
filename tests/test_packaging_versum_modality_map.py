# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""S1 round 2 (packaging smoke test): a unit test importing the module from the
editable ``src/`` tree proves nothing about whether ``versum_modality_map.json``
actually SHIPS in a built wheel — ``[tool.setuptools.package-data]`` could be
wrong, or the file could be missing from the sdist, and every in-tree test would
still pass. This builds a real wheel, installs it (``--no-deps``, so this stays
offline: a packaging check has no business needing the git dependency closure
pip would otherwise fetch) into a disposable venv, and reads the data file back
from its installed location on disk — the same path Python would resolve at
import time, without actually importing ``loomground_solver`` (which the
dependency-free install can't do).

Skips, rather than fails, when the build tooling itself isn't available —
this test is evidence the packaging works when the tooling is there to prove it,
not a hard requirement on every environment that runs the suite.
"""
from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    import build  # noqa: F401
    _HAVE_BUILD = True
except ImportError:
    _HAVE_BUILD = False


pytestmark = pytest.mark.skipif(
    not _HAVE_BUILD, reason="the 'build' package is not installed in this environment")


def test_versum_modality_map_json_ships_in_the_installed_wheel(tmp_path):
    dist_dir = tmp_path / "dist"
    # Isolated build (the default): this environment's own runtime venv has no
    # obligation to carry setuptools/wheel just to run the test suite, and
    # ``build`` fetching its declared build backend into a throwaway env is the
    # normal, supported path (proven to work in this sandbox).
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel",
         "--outdir", str(dist_dir), str(REPO_ROOT)],
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, (
        f"wheel build failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    wheels = list(dist_dir.glob("*.whl"))
    assert wheels, f"no wheel produced in {dist_dir}"
    wheel = wheels[0]

    venv_dir = tmp_path / "venv"
    venv.create(venv_dir, with_pip=True)
    venv_python = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / (
        "python.exe" if sys.platform == "win32" else "python")

    install = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--no-deps", "--quiet", str(wheel)],
        capture_output=True, text=True, timeout=120,
    )
    assert install.returncode == 0, (
        f"wheel install failed:\nSTDOUT:\n{install.stdout}\nSTDERR:\n{install.stderr}")

    # Read the data file back from its INSTALLED location, via the venv's own
    # sysconfig (not this process' import machinery) — proof the packaging
    # metadata, not just the editable source tree, carries the resource. No
    # import of loomground_solver itself: --no-deps means its own declared
    # dependencies (loomground-governance / loomground-deontic) are absent, and
    # this check has no need of them.
    probe = (
        "import json, pathlib, sysconfig\n"
        "p = pathlib.Path(sysconfig.get_path('purelib')) / 'loomground_solver' / "
        "'adapters' / 'versum_modality_map.json'\n"
        "data = json.loads(p.read_text(encoding='utf-8'))\n"
        "assert data['obliged'] == 'obligatory', data\n"
        "assert data['prohibited'] == 'prohibited', data\n"
        "print('installed-json-ok')\n"
    )
    probe_result = subprocess.run(
        [str(venv_python), "-c", probe],
        capture_output=True, text=True, timeout=30,
    )
    assert probe_result.returncode == 0, (
        f"installed JSON probe failed:\nSTDOUT:\n{probe_result.stdout}\n"
        f"STDERR:\n{probe_result.stderr}")
    assert "installed-json-ok" in probe_result.stdout
