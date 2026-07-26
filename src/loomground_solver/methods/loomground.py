"""Loomground governance-language route."""

from ..loomground import reason
from . import register_method


register_method("loomground", "route", reason)
