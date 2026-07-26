# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Optional fingerprint adapters shipped with Solver."""

from .argumentation_schemes import (
    argumentation_schemes,
    register_argumentation_schemes,
)
from .statistics_methods import register_statistics_methods, statistics_methods


def install_reference_filters() -> None:
    """Install every packaged reference filter in the fingerprint registry."""
    register_statistics_methods()
    register_argumentation_schemes()


__all__ = [
    "argumentation_schemes",
    "install_reference_filters",
    "register_argumentation_schemes",
    "register_statistics_methods",
    "statistics_methods",
]
