"""Universal system-adapter boundary with product-native Solver projections."""

from .models import (
    AdapterCapabilities, CoordinateAssignment, NDSystem, SolverProjection,
    SystemIdentity,
)
from .protocol import SystemAdapter
from .registry import AdapterRegistry
from .loomground import LoomgroundAdapter, adapt_loomground
from .deontic import DeonticAdapter, adapt_deontic
from .versum import ClaimAxesDecoder, ClaimAxesProfile, VersumNormSource
from .filters import install_reference_filters

__all__ = [
    "AdapterCapabilities", "AdapterRegistry", "ClaimAxesDecoder",
    "ClaimAxesProfile", "CoordinateAssignment", "DeonticAdapter",
    "LoomgroundAdapter", "NDSystem", "SolverProjection", "SystemAdapter",
    "SystemIdentity", "VersumNormSource", "adapt_deontic", "adapt_loomground",
    "install_reference_filters",
]
