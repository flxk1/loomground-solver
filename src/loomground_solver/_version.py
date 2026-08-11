# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Single runtime version source. Internal by design: a constant, not a surface.

Kept in lockstep with ``pyproject.toml`` by release-please — the trailing
``x-release-please-version`` marker lets the generic updater bump this line on
every release, so the importable ``loomground_solver.__version__`` always
matches the built distribution's version.
"""

__version__ = "0.2.1"  # x-release-please-version
