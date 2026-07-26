"""Safe, versioned selection of installed Solver profiles and rule packs."""
from __future__ import annotations

from dataclasses import dataclass

from .rulepacks import PACKS, GENERIC_PACK


@dataclass(frozen=True)
class SolverConfiguration:
    id: str
    version: str = "1"
    rule_pack: object = GENERIC_PACK


@dataclass(frozen=True)
class NormContractProfile:
    """Host-supplied legal vocabulary for the universal norm contract."""

    id: str
    version: str
    legal_system: str
    conflict_principles: tuple[str, ...]
    incidents: tuple[str, ...]


class ConfigurationResolver:
    def __init__(self, configurations=()):
        defaults = (
            SolverConfiguration("generic", "1", PACKS["generic"]),
            SolverConfiguration("lex-conflict", "1", PACKS["lex-conflict"]),
        )
        chosen = tuple(configurations) or defaults
        self._configs = {c.id: c for c in chosen}

    def resolve(self, spec: str) -> SolverConfiguration:
        name, sep, version = (spec or "generic").partition("@")
        config = self._configs.get(name)
        if config is None:
            raise KeyError(f"unknown solver profile: {name}")
        if sep and version != config.version:
            raise ValueError(f"incompatible solver profile version: {spec}")
        return config
