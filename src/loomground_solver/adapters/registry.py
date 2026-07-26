"""Collision-safe registry for explicitly installed system adapters."""
from __future__ import annotations


class AdapterRegistry:
    def __init__(self, adapters=()):
        self._adapters = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter):
        identity = adapter.identity()
        current = self._adapters.get(identity.system_id)
        if current is not None and current.identity() != identity:
            raise ValueError(f"conflicting adapter for system id {identity.system_id!r}")
        self._adapters[identity.system_id] = adapter
        return adapter

    def for_system(self, system_id: str):
        try:
            return self._adapters[system_id]
        except KeyError as exc:
            raise KeyError(f"no adapter for system {system_id!r}") from exc

    def identities(self):
        return tuple(adapter.identity() for adapter in self._adapters.values())
