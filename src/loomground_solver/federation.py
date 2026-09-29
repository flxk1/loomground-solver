# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Deprecated shim — this module has been renamed to :mod:`loomground_solver.corpus`.

Importing ``loomground_solver.federation`` re-exports the same public objects
and continues to work, but emits a :class:`DeprecationWarning`. Update imports
to ``from loomground_solver import corpus`` (or ``from loomground_solver.corpus
import ...``) before the next major release; this shim will be removed then.
"""
from __future__ import annotations

import warnings

from .corpus import UNDETERMINED, derive_solution, structural_transform

warnings.warn(
    "loomground_solver.federation is deprecated and will be removed in a "
    "future release; import loomground_solver.corpus instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["structural_transform", "derive_solution", "UNDETERMINED"]
